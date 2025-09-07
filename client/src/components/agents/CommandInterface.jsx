// client/src/components/agents/CommandInterface.jsx
import React, { useState, useRef, useEffect } from 'react';
import { 
  Terminal, Send, Download, Upload, FolderOpen, 
  Monitor, Network, Shield, Key, Camera, Loader 
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { useWebSocket } from '../../hooks/useWebsocket';

export default function CommandInterface({ agentId }) {
  const api = useApi();
  const ws = useWebSocket();
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [activeModule, setActiveModule] = useState('terminal');
  const terminalRef = useRef(null);
  const fileInputRef = useRef(null);
  
  useEffect(() => {
    // Subscribe to real-time command output
    if (ws) {
      ws.subscribe(`agent:${agentId}:output`, handleCommandOutput);
      return () => ws.unsubscribe(`agent:${agentId}:output`);
    }
  }, [ws, agentId]);
  
  useEffect(() => {
    // Auto-scroll terminal to bottom
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [output]);
  
  const handleCommandOutput = (data) => {
    setOutput(prev => [...prev, data]);
    if (data.completed) {
      setIsExecuting(false);
    }
  };
  
  const executeCommand = async (cmd, module = 'terminal') => {
    if (!cmd.trim() || isExecuting) return;
    
    setIsExecuting(true);
    setOutput(prev => [...prev, {
      type: 'command',
      content: cmd,
      timestamp: new Date().toISOString()
    }]);
    
    try {
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: module,
        command: cmd,
        parameters: {}
      });
    } catch (error) {
      setOutput(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
      setIsExecuting(false);
    }
    
    setCommand('');
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeCommand(command);
    }
  };
  
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('destination', '/tmp/' + file.name);
    
    setIsExecuting(true);
    try {
      await api.post(`/api/agents/${agentId}/upload`, formData);
      setOutput(prev => [...prev, {
        type: 'success',
        content: `File uploaded: ${file.name}`,
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      setOutput(prev => [...prev, {
        type: 'error',
        content: `Upload failed: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsExecuting(false);
    }
  };
  
  const modules = [
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'files', label: 'File Browser', icon: FolderOpen },
    { id: 'processes', label: 'Processes', icon: Monitor },
    { id: 'network', label: 'Network', icon: Network },
    { id: 'credentials', label: 'Credentials', icon: Key },
    { id: 'screenshot', label: 'Screenshot', icon: Camera },
    { id: 'persistence', label: 'Persistence', icon: Shield }
  ];
  
  const quickCommands = {
    terminal: ['whoami', 'pwd', 'ls -la', 'ps aux', 'netstat -an'],
    files: ['ls', 'pwd', 'cat /etc/passwd', 'find / -name "*.conf"'],
    processes: ['ps aux', 'top -n 1', 'kill -9 <PID>'],
    network: ['ifconfig', 'netstat -an', 'arp -a', 'route -n'],
    credentials: ['dump_creds', 'hashdump', 'enum_tokens'],
    screenshot: ['screenshot', 'webcam_snap'],
    persistence: ['install_persistence', 'create_service', 'add_startup']
  };
  
  return (
    <div className="flex h-[600px]">
      {/* Sidebar */}
      <div className="w-48 bg-gray-900 border-r border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-4">MODULES</h3>
        <div className="space-y-1">
          {modules.map((module) => (
            <button
              key={module.id}
              onClick={() => setActiveModule(module.id)}
              className={`w-full flex items-center px-3 py-2 text-sm rounded transition-colors ${
                activeModule === module.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <module.icon className="h-4 w-4 mr-2" />
              {module.label}
            </button>
          ))}
        </div>
        
        {/* File Upload */}
        <div className="mt-6">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isExecuting}
            className="w-full flex items-center px-3 py-2 text-sm bg-gray-800 text-gray-300 rounded hover:bg-gray-700 disabled:opacity-50"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload File
          </button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Terminal Output */}
        <div
          ref={terminalRef}
          className="flex-1 bg-black p-4 overflow-y-auto font-mono text-sm"
        >
          {output.map((item, index) => (
            <div key={index} className="mb-1">
              {item.type === 'command' && (
                <div className="text-green-400">
                  $ {item.content}
                </div>
              )}
              {item.type === 'output' && (
                <div className="text-gray-300 whitespace-pre-wrap">
                  {item.content}
                </div>
              )}
              {item.type === 'error' && (
                <div className="text-red-400">
                  {item.content}
                </div>
              )}
              {item.type === 'success' && (
                <div className="text-green-400">
                  {item.content}
                </div>
              )}
            </div>
          ))}
          {isExecuting && (
            <div className="flex items-center text-gray-400">
              <Loader className="h-4 w-4 mr-2 animate-spin" />
              Executing...
            </div>
          )}
        </div>
        
        {/* Quick Commands */}
        <div className="bg-gray-900 border-t border-gray-700 p-2">
          <div className="flex space-x-2 overflow-x-auto">
            {quickCommands[activeModule].map((cmd, index) => (
              <button
                key={index}
                onClick={() => executeCommand(cmd, activeModule)}
                disabled={isExecuting}
                className="px-3 py-1 text-xs bg-gray-800 text-gray-300 rounded hover:bg-gray-700 whitespace-nowrap disabled:opacity-50"
              >
                {cmd}
              </button>
            ))}
          </div>
        </div>
        
        {/* Command Input */}
        <div className="bg-gray-800 border-t border-gray-700 p-4">
          <div className="flex space-x-2">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isExecuting}
              placeholder={`Enter ${activeModule} command...`}
              className="flex-1 bg-gray-900 text-white px-4 py-2 rounded border border-gray-700 focus:border-blue-500 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={() => executeCommand(command)}
              disabled={!command.trim() || isExecuting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

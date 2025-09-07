"""
Code obfuscation techniques
"""

import base64
import zlib
import marshal
import types
import random
import string
from typing import Any, Callable

class CodeObfuscation:
    """Python code obfuscation techniques"""
    
    def __init__(self):
        self.obfuscation_layers = [
            self.base64_encode,
            self.compress,
            self.marshal_encode,
            self.string_encode
        ]
    
    def obfuscate_code(self, code: str, layers: int = 2) -> str:
        """Apply multiple layers of obfuscation to Python code"""
        # Compile code first
        try:
            code_obj = compile(code, '<string>', 'exec')
        except SyntaxError:
            raise ValueError("Invalid Python code")
        
        # Apply random obfuscation layers
        obfuscated = marshal.dumps(code_obj)
        
        selected_layers = random.sample(self.obfuscation_layers, 
                                      min(layers, len(self.obfuscation_layers)))
        
        for layer in selected_layers:
            obfuscated = layer(obfuscated)
        
        # Generate decoder
        decoder = self._generate_decoder(selected_layers)
        
        return decoder + f"\nexec(decode('{base64.b64encode(obfuscated).decode()}'))"
    
    def _generate_decoder(self, layers: list) -> str:
        """Generate decoder for obfuscated code"""
        decoder = "import base64, zlib, marshal\n\n"
        decoder += "def decode(data):\n"
        decoder += "    data = base64.b64decode(data)\n"
        
        # Reverse order of layers for decoding
        for layer in reversed(layers):
            if layer == self.base64_encode:
                decoder += "    data = base64.b64decode(data)\n"
            elif layer == self.compress:
                decoder += "    data = zlib.decompress(data)\n"
            elif layer == self.marshal_encode:
                decoder += "    # Marshal decoding handled at exec\n"
            elif layer == self.string_encode:
                decoder += "    data = bytes([b ^ 0x55 for b in data])\n"
        
        decoder += "    return marshal.loads(data)\n"
        
        return decoder
    
    def base64_encode(self, data: bytes) -> bytes:
        """Base64 encoding layer"""
        return base64.b64encode(data)
    
    def compress(self, data: bytes) -> bytes:
        """Compression layer"""
        return zlib.compress(data, 9)
    
    def marshal_encode(self, data: bytes) -> bytes:
        """Marshal encoding layer"""
        # Already marshaled, just return
        return data
    
    def string_encode(self, data: bytes) -> bytes:
        """Simple XOR encoding"""
        return bytes([b ^ 0x55 for b in data])
    
    def variable_renaming(self, code: str) -> str:
        """Rename variables to random names"""
        import ast
        import astor
        
        class VariableRenamer(ast.NodeTransformer):
            def __init__(self):
                self.name_map = {}
            
            def visit_Name(self, node):
                if node.id not in ['print', 'exec', 'eval', 'compile', 
                                  'open', 'input', '__import__']:
                    if node.id not in self.name_map:
                        # Generate random name
                        new_name = ''.join(random.choices(string.ascii_letters, k=8))
                        self.name_map[node.id] = new_name
                    
                    node.id = self.name_map[node.id]
                
                return node
        
        try:
            tree = ast.parse(code)
            renamer = VariableRenamer()
            new_tree = renamer.visit(tree)
            return astor.to_source(new_tree)
        except:
            return code
    
    def control_flow_flattening(self, func: Callable) -> Callable:
        """Flatten control flow of a function"""
        def flattened(*args, **kwargs):
            # Create state machine
            state = 0
            result = None
            
            while state != -1:
                if state == 0:
                    # Original function logic would be split across states
                    result = func(*args, **kwargs)
                    state = -1
                elif state == 1:
                    # Dummy state
                    x = sum([i for i in range(100)])
                    state = 0
                else:
                    state = 0
            
            return result
        
        return flattened
    
    def string_obfuscation(self, text: str) -> tuple:
        """Obfuscate strings in code"""
        # Method 1: Character array
        char_array = [ord(c) for c in text]
        decoder1 = f"''.join([chr(c) for c in {char_array}])"
        
        # Method 2: Base64
        b64_text = base64.b64encode(text.encode()).decode()
        decoder2 = f"__import__('base64').b64decode('{b64_text}').decode()"
        
        # Method 3: Hex encoding
        hex_text = text.encode().hex()
        decoder3 = f"bytes.fromhex('{hex_text}').decode()"
        
        # Method 4: ROT13 (for ASCII text)
        if text.isascii():
            rot13_text = text.translate(str.maketrans(
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'
            ))
            decoder4 = f"'{rot13_text}'.translate(str.maketrans('NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm', 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))"
        else:
            decoder4 = decoder1
        
        return (decoder1, decoder2, decoder3, decoder4)
    
    def dead_code_injection(self, code: str) -> str:
        """Inject dead code to confuse analysis"""
        dead_code_snippets = [
            "if False: x = sum([i**2 for i in range(1000)])",
            "try: pass\nexcept: pass",
            "_ = lambda x: x**2 if x > 0 else x**3",
            "for _ in range(0): print('never')",
            "[i for i in range(0)]",
            "dict(zip([], []))",
        ]
        
        lines = code.split('\n')
        
        # Inject dead code at random positions
        for _ in range(random.randint(2, 5)):
            position = random.randint(0, len(lines))
            dead_code = random.choice(dead_code_snippets)
            lines.insert(position, dead_code)
        
        return '\n'.join(lines)
    
    def opaque_predicates(self, condition: str) -> str:
        """Create opaque predicates (always true/false conditions)"""
        always_true = [
            "7**2 - 1 == 48",
            "len('hello') == 5",
            "2 + 2 == 4",
            "True or False",
            "not False",
            "1 < 2 < 3"
        ]
        
        always_false = [
            "1 > 2",
            "'' == ' '",
            "False and True",
            "0 > 1",
            "len([]) > 0"
        ]
        
        # Combine real condition with opaque predicate
        opaque_true = random.choice(always_true)
        return f"({condition}) and ({opaque_true})"
    
    def dynamic_code_loading(self, code: str) -> str:
        """Generate dynamic code loading wrapper"""
        # Encrypt code
        key = random.randint(1, 255)
        encrypted = bytes([b ^ key for b in code.encode()])
        
        loader = f"""
import types

def load_dynamic():
    encrypted = {list(encrypted)}
    key = {key}
    
    decrypted = bytes([b ^ key for b in encrypted]).decode()
    
    code_obj = compile(decrypted, '<dynamic>', 'exec')
    
    namespace = {{}}
    exec(code_obj, namespace)
    
    return namespace

# Load and execute
dynamic_namespace = load_dynamic()
globals().update(dynamic_namespace)
"""
        
        return loader

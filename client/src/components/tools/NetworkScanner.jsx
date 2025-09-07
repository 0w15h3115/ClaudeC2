// client/src/components/tools/NetworkScanner.jsx
import React, { useState, useEffect } from 'react';
import { 
  Network, Globe, Wifi, Shield, Server, 
  Activity, RefreshCw, Search, AlertCircle 
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function NetworkScanner({ agentId }) {
  const api = useApi();
  const [activeTab, setActiveTab] = useState('connections');
  const [connections, setConnections] = useState([]);
  const [interfaces, setInterfaces] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [arpTable, setArpTable] = useState([]);
  const [scanResults, setScanResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanTarget, setScanTarget] = useState('');
  const [scanPorts, setScanPorts] = useState('1-1000');
  const [isScanning, setIsScanning] = useState(false);
  
  useEffect(() => {
    fetchNetworkInfo();
  }, [agentId, activeTab]);
  
  const fetchNetworkInfo = async () => {
    setLoading(true);
    try {
      switch (activeTab) {
        case 'connections':
          await fetchConnections();
          break;
        case 'interfaces':
          await fetchInterfaces();
          break;
        case 'routes':
          await fetchRoutes();
          break;
        case 'arp':
          await fetchArpTable();
          break;
      }
    } catch (error) {
      console.error('Failed to fetch network info:', error);
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
  
  const fetchConnections = async () => {
    const data = await api.post(`/api/agents/${agentId}/tasks`, {
      module: 'network',
      command: 'connections',
      parameters: {}
    });
    
    const result = await waitForTaskCompletion(data.task_id);
    setConnections(JSON.parse(result.output));
  };
  
  const fetchInterfaces = async () => {
    const data = await api.post(`/api/agents/${agentId}/tasks`, {
      module: 'network',
      command: 'interfaces',
      parameters: {}
    });
    
    const result = await waitForTaskCompletion(data.task_id);
    setInterfaces(JSON.parse(result.output));
  };
  
  const fetchRoutes = async () => {
    const data = await api.post(`/api/agents/${agentId}/tasks`, {
      module: 'network',
      command: 'routes',
      parameters: {}
    });
    
    const result = await waitForTaskCompletion(data.task_id);
    setRoutes(JSON.parse(result.output));
  };
  
  const fetchArpTable = async () => {
    const data = await api.post(`/api/agents/${agentId}/tasks`, {
      module: 'network',
      command: 'arp',
      parameters: {}
    });
    
    const result = await waitForTaskCompletion(data.task_id);
    setArpTable(JSON.parse(result.output));
  };
  
  const performPortScan = async () => {
    if (!scanTarget) return;
    
    setIsScanning(true);
    setScanResults([]);
    
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'network',
        command: 'portscan',
        parameters: {
          target: scanTarget,
          ports: scanPorts
        }
      });
      
      const result = await waitForTaskCompletion(data.task_id, 60000); // 60s timeout for scans
      setScanResults(JSON.parse(result.output));
    } catch (error) {
      console.error('Port scan failed:', error);
    } finally {
      setIsScanning(false);
    }
  };
  
  const getConnectionStateColor = (state) => {
    switch (state) {
      case 'ESTABLISHED':
        return 'text-green-400';
      case 'LISTEN':
        return 'text-blue-400';
      case 'TIME_WAIT':
      case 'CLOSE_WAIT':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };
  
  const tabs = [
    { id: 'connections', label: 'Connections', icon: Network },
    { id: 'interfaces', label: 'Interfaces', icon: Wifi },
    { id: 'routes', label: 'Routes', icon: Server },
    { id: 'arp', label: 'ARP Table', icon: Globe },
    { id: 'scanner', label: 'Port Scanner', icon: Search }
  ];
  
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
      
      {/* Tab Content */}
      <div className="bg-gray-900 rounded-lg p-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <>
            {/* Network Connections */}
            {activeTab === 'connections' && (
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-white">Active Connections</h3>
                  <button
                    onClick={fetchConnections}
                    className="flex items-center px-3 py-1 bg-gray-800 text-gray-300 rounded hover:bg-gray-700"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </button>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider border-b border-gray-800">
                        <th className="pb-2">Protocol</th>
                        <th className="pb-2">Local Address</th>
                        <th className="pb-2">Remote Address</th>
                        <th className="pb-2">State</th>
                        <th className="pb-2">PID</th>
                        <th className="pb-2">Process</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {connections.map((conn, index) => (
                        <tr key={index} className="text-sm">
                          <td className="py-2 text-gray-300">{conn.protocol}</td>
                          <td className="py-2 text-gray-300 font-mono">
                            {conn.localAddr}:{conn.localPort}
                          </td>
                          <td className="py-2 text-gray-300 font-mono">
                            {conn.remoteAddr}:{conn.remotePort}
                          </td>
                          <td className={`py-2 ${getConnectionStateColor(conn.state)}`}>
                            {conn.state}
                          </td>
                          <td className="py-2 text-gray-300">{conn.pid || '-'}</td>
                          <td className="py-2 text-gray-300">{conn.process || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* Network Interfaces */}
            {activeTab === 'interfaces' && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Network Interfaces</h3>
                <div className="space-y-4">
                  {interfaces.map((iface, index) => (
                    <div key={index} className="bg-gray-800 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-white font-medium flex items-center">
                          <Wifi className="h-4 w-4 mr-2" />
                          {iface.name}
                        </h4>
                        <span className={`text-sm ${iface.status === 'up' ? 'text-green-400' : 'text-red-400'}`}>
                          {iface.status}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">IPv4:</span>
                          <p className="text-white font-mono">{iface.ipv4 || 'N/A'}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">IPv6:</span>
                          <p className="text-white font-mono text-xs">{iface.ipv6 || 'N/A'}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">MAC:</span>
                          <p className="text-white font-mono">{iface.mac || 'N/A'}</p>
                        </div>
                        <div>
                          <span className="text-gray-400">MTU:</span>
                          <p className="text-white">{iface.mtu || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Routing Table */}
            {activeTab === 'routes' && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Routing Table</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider border-b border-gray-800">
                        <th className="pb-2">Destination</th>
                        <th className="pb-2">Gateway</th>
                        <th className="pb-2">Netmask</th>
                        <th className="pb-2">Interface</th>
                        <th className="pb-2">Metric</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {routes.map((route, index) => (
                        <tr key={index} className="text-sm">
                          <td className="py-2 text-gray-300 font-mono">{route.destination}</td>
                          <td className="py-2 text-gray-300 font-mono">{route.gateway}</td>
                          <td className="py-2 text-gray-300 font-mono">{route.netmask}</td>
                          <td className="py-2 text-gray-300">{route.interface}</td>
                          <td className="py-2 text-gray-300">{route.metric}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* ARP Table */}
            {activeTab === 'arp' && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">ARP Table</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider border-b border-gray-800">
                        <th className="pb-2">IP Address</th>
                        <th className="pb-2">MAC Address</th>
                        <th className="pb-2">Interface</th>
                        <th className="pb-2">Type</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {arpTable.map((entry, index) => (
                        <tr key={index} className="text-sm">
                          <td className="py-2 text-gray-300 font-mono">{entry.ip}</td>
                          <td className="py-2 text-gray-300 font-mono">{entry.mac}</td>
                          <td className="py-2 text-gray-300">{entry.interface}</td>
                          <td className="py-2 text-gray-300">{entry.type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {/* Port Scanner */}
            {activeTab === 'scanner' && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Port Scanner</h3>
                
                <div className="space-y-4 mb-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Target Host/IP</label>
                      <input
                        type="text"
                        value={scanTarget}
                        onChange={(e) => setScanTarget(e.target.value)}
                        placeholder="192.168.1.1 or hostname"
                        className="w-full px-3 py-2 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Port Range</label>
                      <input
                        type="text"
                        value={scanPorts}
                        onChange={(e) => setScanPorts(e.target.value)}
                        placeholder="1-1000 or 80,443,8080"
                        className="w-full px-3 py-2 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                  </div>
                  
                  <button
                    onClick={performPortScan}
                    disabled={!scanTarget || isScanning}
                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isScanning ? (
                      <>
                        <Activity className="h-4 w-4 mr-2 animate-pulse" />
                        Scanning...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4 mr-2" />
                        Start Scan
                      </>
                    )}
                  </button>
                </div>
                
                {/* Scan Results */}
                {scanResults.length > 0 && (
                  <div>
                    <h4 className="text-white font-medium mb-3">Scan Results</h4>
                    <div className="bg-gray-800 rounded-lg p-4">
                      <div className="grid grid-cols-3 gap-4">
                        {scanResults.map((result, index) => (
                          <div
                            key={index}
                            className={`p-3 rounded border ${
                              result.open ? 'bg-green-900 border-green-700' : 'bg-gray-900 border-gray-700'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-white font-mono">Port {result.port}</span>
                              <span className={`text-sm ${result.open ? 'text-green-400' : 'text-gray-400'}`}>
                                {result.open ? 'Open' : 'Closed'}
                              </span>
                            </div>
                            {result.service && (
                              <p className="text-xs text-gray-400 mt-1">{result.service}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

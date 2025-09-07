// client/src/components/tools/ProcessManager.jsx
import React, { useState, useEffect } from 'react';
import { 
  Activity, Cpu, HardDrive, XCircle, RefreshCw,
  Search, Filter, ChevronUp, ChevronDown
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function ProcessManager({ agentId }) {
  const api = useApi();
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState('cpu');
  const [sortDirection, setSortDirection] = useState('desc');
  const [selectedProcess, setSelectedProcess] = useState(null);
  const [systemStats, setSystemStats] = useState({
    cpu: 0,
    memory: 0,
    disk: 0
  });
  
  useEffect(() => {
    fetchProcesses();
    const interval = setInterval(fetchProcesses, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [agentId]);
  
  const fetchProcesses = async () => {
    setLoading(true);
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'processes',
        command: 'list',
        parameters: {}
      });
      
      const result = await waitForTaskCompletion(data.task_id);
      const processData = JSON.parse(result.output);
      setProcesses(processData.processes);
      setSystemStats(processData.stats);
    } catch (error) {
      console.error('Failed to fetch processes:', error);
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
  
  const killProcess = async (pid) => {
    if (!window.confirm(`Kill process ${pid}?`)) return;
    
    try {
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'processes',
        command: 'kill',
        parameters: { pid }
      });
      
      // Refresh process list
      setTimeout(fetchProcesses, 1000);
    } catch (error) {
      console.error('Failed to kill process:', error);
    }
  };
  
  const sortProcesses = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };
  
  const filteredProcesses = processes
    .filter(proc => 
      proc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      proc.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      proc.pid.toString().includes(searchTerm)
    )
    .sort((a, b) => {
      let aVal = a[sortColumn];
      let bVal = b[sortColumn];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
  
  return (
    <div className="space-y-4">
      {/* System Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">CPU Usage</span>
            <Cpu className="h-4 w-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-white">{systemStats.cpu}%</div>
          <div className="mt-2 bg-gray-800 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-blue-500 h-full transition-all duration-500"
              style={{ width: `${systemStats.cpu}%` }}
            />
          </div>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Memory Usage</span>
            <Activity className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-white">{systemStats.memory}%</div>
          <div className="mt-2 bg-gray-800 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-green-500 h-full transition-all duration-500"
              style={{ width: `${systemStats.memory}%` }}
            />
          </div>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Disk Usage</span>
            <HardDrive className="h-4 w-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-white">{systemStats.disk}%</div>
          <div className="mt-2 bg-gray-800 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-purple-500 h-full transition-all duration-500"
              style={{ width: `${systemStats.disk}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search processes..."
            className="pl-10 pr-4 py-2 bg-gray-900 text-white rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
          />
        </div>
        
        <button
          onClick={fetchProcesses}
          disabled={loading}
          className="flex items-center px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>
      
      {/* Process Table */}
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-800">
              <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                <th className="px-4 py-3">
                  <button
                    onClick={() => sortProcesses('pid')}
                    className="flex items-center space-x-1 hover:text-white"
                  >
                    <span>PID</span>
                    {sortColumn === 'pid' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button
                    onClick={() => sortProcesses('name')}
                    className="flex items-center space-x-1 hover:text-white"
                  >
                    <span>Name</span>
                    {sortColumn === 'name' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button
                    onClick={() => sortProcesses('user')}
                    className="flex items-center space-x-1 hover:text-white"
                  >
                    <span>User</span>
                    {sortColumn === 'user' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button
                    onClick={() => sortProcesses('cpu')}
                    className="flex items-center space-x-1 hover:text-white"
                  >
                    <span>CPU %</span>
                    {sortColumn === 'cpu' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button
                    onClick={() => sortProcesses('memory')}
                    className="flex items-center space-x-1 hover:text-white"
                  >
                    <span>Memory %</span>
                    {sortColumn === 'memory' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {loading ? (
                <tr>
                  <td colSpan="7" className="text-center py-8">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : filteredProcesses.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-8 text-gray-400">
                    No processes found
                  </td>
                </tr>
              ) : (
                filteredProcesses.map((process) => (
                  <tr
                    key={process.pid}
                    className={`hover:bg-gray-800 cursor-pointer ${
                      selectedProcess?.pid === process.pid ? 'bg-gray-800' : ''
                    }`}
                    onClick={() => setSelectedProcess(process)}
                  >
                    <td className="px-4 py-3 text-sm text-white font-mono">
                      {process.pid}
                    </td>
                    <td className="px-4 py-3 text-sm text-white">
                      {process.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {process.user}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center">
                        <span className={`text-white ${process.cpu > 50 ? 'text-red-400' : ''}`}>
                          {process.cpu.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center">
                        <span className={`text-white ${process.memory > 50 ? 'text-yellow-400' : ''}`}>
                          {process.memory.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`inline-flex px-2 py-1 text-xs rounded ${
                        process.status === 'running' 
                          ? 'bg-green-900 text-green-300' 
                          : 'bg-gray-700 text-gray-300'
                      }`}>
                        {process.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          killProcess(process.pid);
                        }}
                        className="p-1 text-red-400 hover:text-red-300"
                        title="Kill Process"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Process Details */}
      {selectedProcess && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-3">Process Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Command Line:</span>
              <p className="text-white mt-1 font-mono text-xs break-all">
                {selectedProcess.cmdline}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Working Directory:</span>
              <p className="text-white mt-1">{selectedProcess.cwd || 'N/A'}</p>
            </div>
            <div>
              <span className="text-gray-400">Parent PID:</span>
              <p className="text-white mt-1">{selectedProcess.ppid || 'N/A'}</p>
            </div>
            <div>
              <span className="text-gray-400">Threads:</span>
              <p className="text-white mt-1">{selectedProcess.threads || 'N/A'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// client/src/components/agents/AgentDetails.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Monitor, Globe, Cpu, HardDrive, User, Shield, 
  Clock, Activity, Terminal, X, Trash2, RefreshCw 
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import CommandInterface from './CommandInterface';
import TaskHistory from './TaskHistory';

export default function AgentDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const api = useApi();
  const [agent, setAgent] = useState(null);
  const [activeTab, setActiveTab] = useState('info');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchAgentDetails();
    const interval = setInterval(fetchAgentDetails, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [id]);
  
  const fetchAgentDetails = async () => {
    try {
      const data = await api.get(`/api/agents/${id}`);
      setAgent(data);
    } catch (error) {
      console.error('Failed to fetch agent details:', error);
      if (error.status === 404) {
        navigate('/agents');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const handleDeleteAgent = async () => {
    if (window.confirm('Are you sure you want to remove this agent?')) {
      try {
        await api.delete(`/api/agents/${id}`);
        navigate('/agents');
      } catch (error) {
        console.error('Failed to delete agent:', error);
      }
    }
  };
  
  const handleReconnect = async () => {
    try {
      await api.post(`/api/agents/${id}/reconnect`);
      await fetchAgentDetails();
    } catch (error) {
      console.error('Failed to reconnect agent:', error);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (!agent) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-400">Agent not found</p>
      </div>
    );
  }
  
  const tabs = [
    { id: 'info', label: 'Information', icon: Monitor },
    { id: 'command', label: 'Command', icon: Terminal },
    { id: 'tasks', label: 'Task History', icon: Activity }
  ];
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">
              {agent.hostname || `Agent ${agent.id.slice(0, 8)}`}
            </h1>
            <div className="flex items-center space-x-4 text-sm text-gray-400">
              <span className="flex items-center">
                <Globe className="h-4 w-4 mr-1" />
                {agent.external_ip}
              </span>
              <span className="flex items-center">
                <Clock className="h-4 w-4 mr-1" />
                Last seen: {new Date(agent.last_seen).toLocaleString()}
              </span>
              <span className={`flex items-center px-2 py-1 rounded ${
                agent.status === 'active' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
              }`}>
                <span className={`w-2 h-2 rounded-full mr-2 ${
                  agent.status === 'active' ? 'bg-green-500' : 'bg-red-500'
                }`}></span>
                {agent.status}
              </span>
            </div>
          </div>
          
          <div className="flex space-x-2">
            {agent.status === 'disconnected' && (
              <button
                onClick={handleReconnect}
                className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={handleDeleteAgent}
              className="p-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => navigate('/agents')}
              className="p-2 bg-gray-700 text-white rounded hover:bg-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="flex space-x-1 border-b border-gray-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-gray-700 text-white border-b-2 border-blue-500'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Tab Content */}
      <div className="bg-gray-800 rounded-lg p-6">
        {activeTab === 'info' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* System Information */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Monitor className="h-5 w-5 mr-2" />
                System Information
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-400">Operating System</dt>
                  <dd className="text-white">{agent.os} {agent.os_version}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Architecture</dt>
                  <dd className="text-white">{agent.arch}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Username</dt>
                  <dd className="text-white flex items-center">
                    <User className="h-4 w-4 mr-1" />
                    {agent.username}
                    {agent.is_admin && (
                      <Shield className="h-4 w-4 ml-2 text-yellow-500" />
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Process ID</dt>
                  <dd className="text-white">{agent.pid}</dd>
                </div>
              </dl>
            </div>
            
            {/* Hardware Information */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Cpu className="h-5 w-5 mr-2" />
                Hardware Information
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-400">CPU</dt>
                  <dd className="text-white">{agent.cpu_info}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Memory</dt>
                  <dd className="text-white">{agent.memory_total} GB</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Disk Space</dt>
                  <dd className="text-white">{agent.disk_total} GB</dd>
                </div>
              </dl>
            </div>
            
            {/* Network Information */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Globe className="h-5 w-5 mr-2" />
                Network Information
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-400">Internal IP</dt>
                  <dd className="text-white">{agent.internal_ip}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">External IP</dt>
                  <dd className="text-white">{agent.external_ip}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Domain</dt>
                  <dd className="text-white">{agent.domain || 'N/A'}</dd>
                </div>
              </dl>
            </div>
            
            {/* Agent Configuration */}
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Shield className="h-5 w-5 mr-2" />
                Agent Configuration
              </h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm text-gray-400">Agent Version</dt>
                  <dd className="text-white">{agent.version}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Communication Protocol</dt>
                  <dd className="text-white">{agent.protocol}</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">Check-in Interval</dt>
                  <dd className="text-white">{agent.checkin_interval}s</dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-400">First Seen</dt>
                  <dd className="text-white">{new Date(agent.first_seen).toLocaleString()}</dd>
                </div>
              </dl>
            </div>
          </div>
        )}
        
        {activeTab === 'command' && <CommandInterface agentId={agent.id} />}
        {activeTab === 'tasks' && <TaskHistory agentId={agent.id} />}
      </div>
    </div>
  );
}

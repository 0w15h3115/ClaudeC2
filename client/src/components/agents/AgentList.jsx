// client/src/components/dashboard/AgentList.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Monitor, Globe, Clock, MoreVertical } from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function AgentList({ limit }) {
  const api = useApi();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [limit]);
  
  const fetchAgents = async () => {
    try {
      const data = await api.get(`/api/agents?status=active&limit=${limit || 100}`);
      setAgents(data);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'idle':
        return 'bg-yellow-500';
      case 'disconnected':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };
  
  const getOSIcon = (os) => {
    switch (os?.toLowerCase()) {
      case 'windows':
        return '🪟';
      case 'linux':
        return '🐧';
      case 'macos':
        return '🍎';
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (agents.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-400">No active agents</p>
      </div>
    );
  }
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
            <th className="pb-3">Agent</th>
            <th className="pb-3">System</th>
            <th className="pb-3">Location</th>
            <th className="pb-3">Last Seen</th>
            <th className="pb-3">Status</th>
            <th className="pb-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {agents.map((agent) => (
            <tr key={agent.id} className="hover:bg-gray-700 transition-colors">
              <td className="py-3">
                <Link
                  to={`/agents/${agent.id}`}
                  className="text-blue-400 hover:text-blue-300 font-medium"
                >
                  {agent.hostname || agent.id.slice(0, 8)}
                </Link>
              </td>
              <td className="py-3">
                <div className="flex items-center space-x-2">
                  <span>{getOSIcon(agent.os)}</span>
                  <span className="text-sm text-gray-300">
                    {agent.os} {agent.arch}
                  </span>
                </div>
              </td>
              <td className="py-3">
                <div className="flex items-center space-x-1 text-sm text-gray-300">
                  <Globe className="h-4 w-4" />
                  <span>{agent.external_ip || 'Unknown'}</span>
                </div>
              </td>
              <td className="py-3">
                <div className="flex items-center space-x-1 text-sm text-gray-300">
                  <Clock className="h-4 w-4" />
                  <span>{new Date(agent.last_seen).toLocaleTimeString()}</span>
                </div>
              </td>
              <td className="py-3">
                <span className="flex items-center">
                  <span className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)} mr-2`}></span>
                  <span className="text-sm capitalize">{agent.status}</span>
                </span>
              </td>
              <td className="py-3">
                <button className="text-gray-400 hover:text-white">
                  <MoreVertical className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {limit && agents.length === limit && (
        <div className="mt-4 text-center">
          <Link
            to="/agents"
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            View all agents →
          </Link>
        </div>
      )}
    </div>
  );
}

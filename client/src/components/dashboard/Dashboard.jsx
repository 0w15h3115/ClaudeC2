// client/src/components/dashboard/Dashboard.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Users, Server, AlertTriangle, TrendingUp, Clock } from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import AgentList from '../agents/AgentList';
import Statistics from './Statistics';

export default function Dashboard() {
  const api = useApi();
  const [stats, setStats] = useState({
    totalAgents: 0,
    activeAgents: 0,
    totalTasks: 0,
    completedTasks: 0,
    activeListeners: 0,
    alerts: 0
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);
  
  const fetchDashboardData = async () => {
    try {
      const [statsData, activityData] = await Promise.all([
        api.get('/api/stats'),
        api.get('/api/activity/recent')
      ]);
      
      setStats(statsData);
      setRecentActivity(activityData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const statCards = [
    {
      title: 'Active Agents',
      value: stats.activeAgents,
      total: stats.totalAgents,
      icon: Users,
      color: 'bg-green-500',
      link: '/agents'
    },
    {
      title: 'Running Tasks',
      value: stats.totalTasks - stats.completedTasks,
      total: stats.totalTasks,
      icon: Activity,
      color: 'bg-blue-500',
      link: '/tasks'
    },
    {
      title: 'Active Listeners',
      value: stats.activeListeners,
      icon: Server,
      color: 'bg-purple-500',
      link: '/listeners'
    },
    {
      title: 'Alerts',
      value: stats.alerts,
      icon: AlertTriangle,
      color: stats.alerts > 0 ? 'bg-red-500' : 'bg-gray-500',
      link: '/alerts'
    }
  ];
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <div className="text-sm text-gray-400">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card, index) => (
          <Link
            key={index}
            to={card.link}
            className="bg-gray-800 rounded-lg p-6 hover:bg-gray-750 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">{card.title}</p>
                <p className="text-2xl font-bold text-white mt-1">
                  {card.value}
                  {card.total && (
                    <span className="text-sm text-gray-400 font-normal">
                      /{card.total}
                    </span>
                  )}
                </p>
              </div>
              <div className={`${card.color} p-3 rounded-lg`}>
                <card.icon className="h-6 w-6 text-white" />
              </div>
            </div>
          </Link>
        ))}
      </div>
      
      {/* Charts and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2" />
            Statistics
          </h2>
          <Statistics />
        </div>
        
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2" />
            Recent Activity
          </h2>
          <div className="space-y-3">
            {recentActivity.length > 0 ? (
              recentActivity.map((activity, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  <div className="flex-1">
                    <p className="text-sm text-white">{activity.message}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-sm">No recent activity</p>
            )}
          </div>
        </div>
      </div>
      
      {/* Active Agents */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Active Agents</h2>
        <AgentList limit={5} />
      </div>
    </div>
  );
}

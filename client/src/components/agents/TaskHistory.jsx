// client/src/components/agents/TaskHistory.jsx
import React, { useEffect, useState } from 'react';
import { 
  Clock, CheckCircle, XCircle, AlertCircle, 
  ChevronDown, ChevronRight, Download, Eye 
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function TaskHistory({ agentId }) {
  const api = useApi();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedTasks, setExpandedTasks] = useState(new Set());
  const [filter, setFilter] = useState('all'); // all, completed, failed, pending
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  useEffect(() => {
    fetchTasks();
  }, [agentId, filter, page]);
  
  const fetchTasks = async () => {
    try {
      const data = await api.get(`/api/agents/${agentId}/tasks?status=${filter}&page=${page}&limit=20`);
      setTasks(data.tasks);
      setTotalPages(data.totalPages);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleTaskExpansion = (taskId) => {
    const newExpanded = new Set(expandedTasks);
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId);
    } else {
      newExpanded.add(taskId);
    }
    setExpandedTasks(newExpanded);
  };
  
  const downloadTaskOutput = async (taskId) => {
    try {
      const response = await api.get(`/api/tasks/${taskId}/output`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `task_${taskId}_output.txt`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to download output:', error);
    }
  };
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
      case 'running':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'pending':
      case 'running':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center justify-between">
        <div className="flex space-x-2">
          {['all', 'completed', 'failed', 'pending'].map((status) => (
            <button
              key={status}
              onClick={() => {
                setFilter(status);
                setPage(1);
              }}
              className={`px-3 py-1 text-sm rounded capitalize ${
                filter === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
        
        <div className="text-sm text-gray-400">
          Total: {tasks.length} tasks
        </div>
      </div>
      
      {/* Task List */}
      <div className="space-y-2">
        {tasks.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No tasks found
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className="bg-gray-900 rounded-lg border border-gray-700"
            >
              {/* Task Header */}
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800"
                onClick={() => toggleTaskExpansion(task.id)}
              >
                <div className="flex items-center space-x-3">
                  <button className="text-gray-400">
                    {expandedTasks.has(task.id) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                  {getStatusIcon(task.status)}
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-white">
                        {task.module}
                      </span>
                      <span className="text-gray-400">→</span>
                      <code className="text-sm text-blue-400">
                        {task.command}
                      </code>
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-gray-400 mt-1">
                      <span>{new Date(task.created_at).toLocaleString()}</span>
                      {task.completed_at && (
                        <span>
                          Duration: {Math.round((new Date(task.completed_at) - new Date(task.created_at)) / 1000)}s
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className={`text-sm capitalize ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                  {task.output && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        downloadTaskOutput(task.id);
                      }}
                      className="p-1 text-gray-400 hover:text-white"
                      title="Download Output"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
              
              {/* Task Details (Expanded) */}
              {expandedTasks.has(task.id) && (
                <div className="border-t border-gray-700 p-4">
                  <div className="space-y-3">
                    {/* Task Info */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Task ID:</span>
                        <span className="ml-2 text-white font-mono">
                          {task.id}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Created By:</span>
                        <span className="ml-2 text-white">
                          {task.created_by}
                        </span>
                      </div>
                    </div>
                    
                    {/* Task Output */}
                    {task.output && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-gray-400">Output:</span>
                          <button
                            onClick={() => toggleTaskExpansion(task.id + '_output')}
                            className="text-xs text-blue-400 hover:text-blue-300 flex items-center"
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            {expandedTasks.has(task.id + '_output') ? 'Hide' : 'Show'}
                          </button>
                        </div>
                        {expandedTasks.has(task.id + '_output') && (
                          <pre className="bg-black text-gray-300 p-3 rounded text-xs overflow-x-auto max-h-64 overflow-y-auto">
                            {task.output}
                          </pre>
                        )}
                      </div>
                    )}
                    
                    {/* Task Error */}
                    {task.error && (
                      <div>
                        <span className="text-sm text-gray-400">Error:</span>
                        <div className="mt-1 bg-red-900 bg-opacity-20 text-red-400 p-3 rounded text-sm">
                          {task.error}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center space-x-2 pt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm bg-gray-700 text-gray-300 rounded hover:bg-gray-600 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-3 py-1 text-sm bg-gray-700 text-gray-300 rounded hover:bg-gray-600 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

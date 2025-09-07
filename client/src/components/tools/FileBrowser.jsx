// client/src/components/tools/FileBrowser.jsx
import React, { useState, useEffect } from 'react';
import { 
  Folder, File, FolderOpen, ChevronRight, ChevronDown,
  Download, Upload, Trash2, Edit, Save, X, Home
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';

export default function FileBrowser({ agentId }) {
  const api = useApi();
  const [currentPath, setCurrentPath] = useState('/');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [editingFile, setEditingFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  
  useEffect(() => {
    fetchFiles(currentPath);
  }, [agentId, currentPath]);
  
  const fetchFiles = async (path) => {
    setLoading(true);
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'files',
        command: 'list',
        parameters: { path }
      });
      
      // Wait for task completion
      const result = await waitForTaskCompletion(data.task_id);
      setFiles(JSON.parse(result.output));
    } catch (error) {
      console.error('Failed to fetch files:', error);
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
  
  const navigateToFolder = (folder) => {
    const newPath = currentPath === '/' 
      ? `/${folder}` 
      : `${currentPath}/${folder}`;
    setCurrentPath(newPath.replace(/\/+/g, '/'));
  };
  
  const navigateUp = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    setCurrentPath('/' + parts.join('/'));
  };
  
  const downloadFile = async (file) => {
    try {
      const data = await api.post(`/api/agents/${agentId}/download`, {
        path: `${currentPath}/${file.name}`.replace(/\/+/g, '/')
      });
      
      // Create download link
      const blob = new Blob([data.content], { type: 'application/octet-stream' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download file:', error);
    }
  };
  
  const viewFile = async (file) => {
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'files',
        command: 'read',
        parameters: { 
          path: `${currentPath}/${file.name}`.replace(/\/+/g, '/') 
        }
      });
      
      const result = await waitForTaskCompletion(data.task_id);
      setSelectedFile(file);
      setFileContent(result.output);
    } catch (error) {
      console.error('Failed to read file:', error);
    }
  };
  
  const saveFile = async () => {
    try {
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'files',
        command: 'write',
        parameters: {
          path: `${currentPath}/${editingFile.name}`.replace(/\/+/g, '/'),
          content: fileContent
        }
      });
      
      setEditingFile(null);
      fetchFiles(currentPath);
    } catch (error) {
      console.error('Failed to save file:', error);
    }
  };
  
  const deleteFile = async (file) => {
    if (!window.confirm(`Delete ${file.name}?`)) return;
    
    try {
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'files',
        command: 'delete',
        parameters: {
          path: `${currentPath}/${file.name}`.replace(/\/+/g, '/')
        }
      });
      
      fetchFiles(currentPath);
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  return (
    <div className="flex h-[600px]">
      {/* File List */}
      <div className="flex-1 border-r border-gray-700">
        {/* Path Bar */}
        <div className="bg-gray-900 border-b border-gray-700 p-3 flex items-center space-x-2">
          <button
            onClick={() => setCurrentPath('/')}
            className="p-1 text-gray-400 hover:text-white"
          >
            <Home className="h-4 w-4" />
          </button>
          <span className="text-gray-400">/</span>
          {currentPath.split('/').filter(Boolean).map((part, index, arr) => (
            <React.Fragment key={index}>
              <button
                onClick={() => {
                  const newPath = '/' + arr.slice(0, index + 1).join('/');
                  setCurrentPath(newPath);
                }}
                className="text-blue-400 hover:text-blue-300"
              >
                {part}
              </button>
              {index < arr.length - 1 && <span className="text-gray-400">/</span>}
            </React.Fragment>
          ))}
        </div>
        
        {/* File Table */}
        <div className="overflow-y-auto h-[calc(100%-48px)]">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-800 sticky top-0">
                <tr className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2">Modified</th>
                  <th className="px-4 py-2">Permissions</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {currentPath !== '/' && (
                  <tr
                    className="hover:bg-gray-800 cursor-pointer"
                    onClick={navigateUp}
                  >
                    <td className="px-4 py-2 flex items-center space-x-2">
                      <Folder className="h-4 w-4 text-yellow-500" />
                      <span className="text-gray-300">..</span>
                    </td>
                    <td colSpan="4"></td>
                  </tr>
                )}
                {files.map((file, index) => (
                  <tr
                    key={index}
                    className="hover:bg-gray-800 cursor-pointer"
                    onClick={() => file.isDirectory ? navigateToFolder(file.name) : viewFile(file)}
                  >
                    <td className="px-4 py-2 flex items-center space-x-2">
                      {file.isDirectory ? (
                        <Folder className="h-4 w-4 text-yellow-500" />
                      ) : (
                        <File className="h-4 w-4 text-gray-400" />
                      )}
                      <span className="text-gray-300">{file.name}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-400">
                      {file.isDirectory ? '-' : formatFileSize(file.size)}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-400">
                      {new Date(file.modified).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-sm font-mono text-gray-400">
                      {file.permissions}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex space-x-1">
                        {!file.isDirectory && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              downloadFile(file);
                            }}
                            className="p-1 text-gray-400 hover:text-white"
                            title="Download"
                          >
                            <Download className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteFile(file);
                          }}
                          className="p-1 text-gray-400 hover:text-red-400"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      
      {/* File Viewer/Editor */}
      {selectedFile && (
        <div className="w-1/2 flex flex-col">
          <div className="bg-gray-900 border-b border-gray-700 p-3 flex items-center justify-between">
            <span className="text-white font-medium">{selectedFile.name}</span>
            <div className="flex space-x-2">
              {editingFile ? (
                <>
                  <button
                    onClick={saveFile}
                    className="p-1 text-green-400 hover:text-green-300"
                    title="Save"
                  >
                    <Save className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingFile(null);
                      setFileContent(selectedFile.content);
                    }}
                    className="p-1 text-gray-400 hover:text-white"
                    title="Cancel"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setEditingFile(selectedFile)}
                    className="p-1 text-gray-400 hover:text-white"
                    title="Edit"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="p-1 text-gray-400 hover:text-white"
                    title="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </>
              )}
            </div>
          </div>
          
          <div className="flex-1 overflow-auto">
            {editingFile ? (
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="w-full h-full bg-gray-900 text-gray-300 p-4 font-mono text-sm resize-none focus:outline-none"
                spellCheck={false}
              />
            ) : (
              <pre className="bg-gray-900 text-gray-300 p-4 font-mono text-sm">
                {fileContent}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

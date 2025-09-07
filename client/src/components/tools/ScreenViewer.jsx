// client/src/components/tools/ScreenViewer.jsx
import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, Monitor, RefreshCw, Download, 
  ZoomIn, ZoomOut, Maximize2, Play, Pause 
} from 'lucide-react';
import { useApi } from '../../hooks/useApi';
import { useWebSocket } from '../../hooks/useWebsocket';

export default function ScreenViewer({ agentId }) {
  const api = useApi();
  const ws = useWebSocket();
  const [screenshot, setScreenshot] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamInterval, setStreamInterval] = useState(1000); // ms
  const [zoom, setZoom] = useState(100);
  const [loading, setLoading] = useState(false);
  const imageRef = useRef(null);
  const streamIntervalRef = useRef(null);
  
  useEffect(() => {
    // Subscribe to real-time screenshot updates
    if (ws && isStreaming) {
      ws.subscribe(`agent:${agentId}:screenshot`, handleScreenshotUpdate);
      return () => ws.unsubscribe(`agent:${agentId}:screenshot`);
    }
  }, [ws, agentId, isStreaming]);
  
  useEffect(() => {
    // Cleanup stream interval on unmount
    return () => {
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
      }
    };
  }, []);
  
  const handleScreenshotUpdate = (data) => {
    setScreenshot({
      data: data.image,
      timestamp: data.timestamp,
      resolution: data.resolution
    });
  };
  
  const captureScreenshot = async () => {
    setLoading(true);
    try {
      const data = await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'screenshot',
        command: 'capture',
        parameters: {}
      });
      
      const result = await waitForTaskCompletion(data.task_id);
      const screenshotData = JSON.parse(result.output);
      setScreenshot(screenshotData);
    } catch (error) {
      console.error('Failed to capture screenshot:', error);
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
  
  const toggleStreaming = async () => {
    if (isStreaming) {
      // Stop streaming
      setIsStreaming(false);
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
      }
      
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'screenshot',
        command: 'stop_stream',
        parameters: {}
      });
    } else {
      // Start streaming
      setIsStreaming(true);
      
      await api.post(`/api/agents/${agentId}/tasks`, {
        module: 'screenshot',
        command: 'start_stream',
        parameters: { interval: streamInterval }
      });
      
      // Also set up periodic capture as fallback
      streamIntervalRef.current = setInterval(captureScreenshot, streamInterval);
    }
  };
  
  const downloadScreenshot = () => {
    if (!screenshot) return;
    
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${screenshot.data}`;
    link.download = `screenshot_${agentId}_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  const handleZoom = (delta) => {
    const newZoom = Math.max(25, Math.min(200, zoom + delta));
    setZoom(newZoom);
  };
  
  const fitToScreen = () => {
    if (!imageRef.current || !screenshot) return;
    
    const container = imageRef.current.parentElement;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const imageWidth = screenshot.resolution.width;
    const imageHeight = screenshot.resolution.height;
    
    const widthRatio = containerWidth / imageWidth;
    const heightRatio = containerHeight / imageHeight;
    
    const optimalZoom = Math.min(widthRatio, heightRatio) * 100;
    setZoom(Math.floor(optimalZoom));
  };
  
  return (
    <div className="flex flex-col h-[600px]">
      {/* Controls */}
      <div className="bg-gray-900 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={captureScreenshot}
              disabled={loading || isStreaming}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              <Camera className="h-4 w-4 mr-2" />
              Capture
            </button>
            
            <button
              onClick={toggleStreaming}
              className={`flex items-center px-4 py-2 rounded ${
                isStreaming 
                  ? 'bg-red-600 hover:bg-red-700' 
                  : 'bg-green-600 hover:bg-green-700'
              } text-white`}
            >
              {isStreaming ? (
                <>
                  <Pause className="h-4 w-4 mr-2" />
                  Stop Stream
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Stream
                </>
              )}
            </button>
            
            {!isStreaming && (
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-400">Interval:</label>
                <select
                  value={streamInterval}
                  onChange={(e) => setStreamInterval(Number(e.target.value))}
                  className="px-2 py-1 bg-gray-800 text-white rounded border border-gray-700 focus:border-blue-500 focus:outline-none text-sm"
                >
                  <option value={500}>0.5s</option>
                  <option value={1000}>1s</option>
                  <option value={2000}>2s</option>
                  <option value={5000}>5s</option>
                </select>
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Zoom Controls */}
            <div className="flex items-center space-x-1 bg-gray-800 rounded px-2 py-1">
              <button
                onClick={() => handleZoom(-10)}
                className="p-1 text-gray-400 hover:text-white"
              >
                <ZoomOut className="h-4 w-4" />
              </button>
              <span className="text-sm text-white px-2">{zoom}%</span>
              <button
                onClick={() => handleZoom(10)}
                className="p-1 text-gray-400 hover:text-white"
              >
                <ZoomIn className="h-4 w-4" />
              </button>
            </div>
            
            <button
              onClick={fitToScreen}
              className="p-2 bg-gray-800 text-gray-400 rounded hover:text-white"
              title="Fit to screen"
            >
              <Maximize2 className="h-4 w-4" />
            </button>
            
            <button
              onClick={downloadScreenshot}
              disabled={!screenshot}
              className="p-2 bg-gray-800 text-gray-400 rounded hover:text-white disabled:opacity-50"
              title="Download"
            >
              <Download className="h-4 w-4" />
            </button>
          </div>
        </div>
        
        {/* Status Bar */}
        {screenshot && (
          <div className="flex items-center space-x-4 mt-3 text-sm text-gray-400">
            <span className="flex items-center">
              <Monitor className="h-4 w-4 mr-1" />
              {screenshot.resolution.width} × {screenshot.resolution.height}
            </span>
            <span>
              Captured: {new Date(screenshot.timestamp).toLocaleTimeString()}
            </span>
            {isStreaming && (
              <span className="flex items-center text-green-400">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
                Live Stream
              </span>
            )}
          </div>
        )}
      </div>
      
      {/* Screenshot Display */}
      <div className="flex-1 bg-black overflow-auto relative">
        {loading && !screenshot && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center space-x-2 text-gray-400">
              <RefreshCw className="h-6 w-6 animate-spin" />
              <span>Capturing screenshot...</span>
            </div>
          </div>
        )}
        
        {screenshot && (
          <div className="flex items-center justify-center min-h-full p-4">
            <img
              ref={imageRef}
              src={`data:image/png;base64,${screenshot.data}`}
              alt="Remote Screen"
              style={{
                width: `${zoom}%`,
                height: 'auto',
                maxWidth: 'none'
              }}
              className="shadow-2xl"
            />
          </div>
        )}
        
        {!screenshot && !loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Monitor className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No screenshot available</p>
              <p className="text-sm text-gray-500 mt-2">
                Click "Capture" to take a screenshot
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

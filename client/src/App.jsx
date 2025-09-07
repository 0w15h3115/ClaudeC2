// client/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { useAuth } from './hooks/useAuth';

// Components
import Layout from './components/common/Layout';
import Login from './components/auth/Login';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Dashboard from './components/dashboard/Dashboard';
import AgentDetails from './components/agents/AgentDetails';


// Pages (simplified imports for now)
const AgentsPage = () => <div>Agents Page</div>;
const TasksPage = () => <div>Tasks Page</div>;
const ListenersPage = () => <div>Listeners Page</div>;
const PayloadsPage = () => <div>Payloads Page</div>;
const CredentialsPage = () => <div>Credentials Page</div>;
const FileManagerPage = () => <div>File Manager Page</div>;
const NetworkToolsPage = () => <div>Network Tools Page</div>;
const LogsPage = () => <div>Logs Page</div>;
const AlertsPage = () => <div>Alerts Page</div>;
const ReportsPage = () => <div>Reports Page</div>;
const DatabasePage = () => <div>Database Page</div>;
const SecurityPage = () => <div>Security Page</div>;
const SettingsPage = () => <div>Settings Page</div>;

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  
  return (
    <Routes>
      {/* Public routes */}
      <Route 
        path="/login" 
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} 
      />
      
      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        
        {/* Agents */}
        <Route path="agents" element={<AgentsPage />} />
        <Route path="agents/:id" element={<AgentDetails />} />
        
        {/* Tasks */}
        <Route path="tasks" element={<TasksPage />} />
        
        {/* Listeners */}
        <Route path="listeners" element={<ListenersPage />} />
        
        {/* Tools */}
        <Route path="payloads" element={<PayloadsPage />} />
        <Route path="credentials" element={<CredentialsPage />} />
        <Route path="files" element={<FileManagerPage />} />
        <Route path="network" element={<NetworkToolsPage />} />
        
        {/* Monitoring */}
        <Route path="logs" element={<LogsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        
        {/* System */}
        <Route path="database" element={<DatabasePage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      {/* Catch all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <WebSocketProvider>
          <AppRoutes />
        </WebSocketProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
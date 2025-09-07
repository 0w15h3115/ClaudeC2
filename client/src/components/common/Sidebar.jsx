// client/src/components/common/Sidebar.jsx
import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Home, Users, Terminal, Activity, Server, 
  FileText, Shield, Settings, AlertTriangle,
  Package, Clock, Database, Globe, Key
} from 'lucide-react';

export default function Sidebar({ isOpen }) {
  const location = useLocation();
  
  const menuItems = [
    {
      section: 'Main',
      items: [
        { path: '/dashboard', label: 'Dashboard', icon: Home },
        { path: '/agents', label: 'Agents', icon: Users },
        { path: '/tasks', label: 'Tasks', icon: Activity },
        { path: '/listeners', label: 'Listeners', icon: Server }
      ]
    },
    {
      section: 'Tools',
      items: [
        { path: '/payloads', label: 'Payloads', icon: Package },
        { path: '/credentials', label: 'Credentials', icon: Key },
        { path: '/files', label: 'File Manager', icon: FileText },
        { path: '/network', label: 'Network Tools', icon: Globe }
      ]
    },
    {
      section: 'Monitoring',
      items: [
        { path: '/logs', label: 'Logs', icon: Clock },
        { path: '/alerts', label: 'Alerts', icon: AlertTriangle },
        { path: '/reports', label: 'Reports', icon: FileText }
      ]
    },
    {
      section: 'System',
      items: [
        { path: '/database', label: 'Database', icon: Database },
        { path: '/security', label: 'Security', icon: Shield },
        { path: '/settings', label: 'Settings', icon: Settings }
      ]
    }
  ];
  
  return (
    <aside className={`fixed left-0 top-0 h-full bg-gray-800 border-r border-gray-700 transition-all duration-200 z-40 ${
      isOpen ? 'w-64' : 'w-0 overflow-hidden'
    }`}>
      <div className="h-full pt-20 pb-4 overflow-y-auto">
        {menuItems.map((section, index) => (
          <div key={index} className="mb-6">
            <h3 className="px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              {section.section}
            </h3>
            <nav className="space-y-1 px-3">
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) => `
                      flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors
                      ${isActive 
                        ? 'bg-gray-900 text-white' 
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                      }
                    `}
                  >
                    <Icon className="h-5 w-5 mr-3 flex-shrink-0" />
                    <span>{item.label}</span>
                    {item.path === '/alerts' && (
                      <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                        3
                      </span>
                    )}
                    {item.path === '/agents' && (
                      <span className="ml-auto bg-green-500 text-white text-xs rounded-full px-2 py-0.5">
                        12
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        ))}
        
        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700">
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>Server Online</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}

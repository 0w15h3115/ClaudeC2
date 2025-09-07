// client/src/hooks/useApi.js
import { useState, useCallback, useEffect } from 'react';
import apiService from '../services/api';

export function useApi() {
  return apiService;
}

// Hook for API calls with loading state
export function useApiCall(apiFunction) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  
  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);
  
  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);
  
  return {
    execute,
    loading,
    error,
    data,
    reset
  };
}

// Hook for paginated API calls
export function usePaginatedApi(apiFunction, initialParams = {}) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [params, setParams] = useState(initialParams);
  
  const fetchPage = useCallback(async (pageNum = page) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction({
        ...params,
        page: pageNum,
        limit: params.limit || 20
      });
      
      setItems(result.items || result.data || []);
      setTotalPages(result.totalPages || 1);
      setPage(pageNum);
      
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction, params, page]);
  
  const nextPage = useCallback(() => {
    if (page < totalPages) {
      return fetchPage(page + 1);
    }
  }, [page, totalPages, fetchPage]);
  
  const previousPage = useCallback(() => {
    if (page > 1) {
      return fetchPage(page - 1);
    }
  }, [page, fetchPage]);
  
  const updateParams = useCallback((newParams) => {
    setParams(prev => ({ ...prev, ...newParams }));
    setPage(1); // Reset to first page on param change
  }, []);
  
  return {
    items,
    page,
    totalPages,
    loading,
    error,
    fetchPage,
    nextPage,
    previousPage,
    updateParams,
    hasNextPage: page < totalPages,
    hasPreviousPage: page > 1
  };
}

// Hook for polling API endpoint
export function useApiPolling(apiFunction, interval = 5000, enabled = true) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const fetch = useCallback(async () => {
    if (!enabled) return;
    
    setLoading(true);
    try {
      const result = await apiFunction();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [apiFunction, enabled]);
  
  useEffect(() => {
    if (!enabled) return;
    
    // Initial fetch
    fetch();
    
    // Set up polling
    const timer = setInterval(fetch, interval);
    
    return () => clearInterval(timer);
  }, [fetch, interval, enabled]);
  
  return { data, error, loading, refetch: fetch };
}

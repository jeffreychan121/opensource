import { useState, useEffect, useCallback } from 'react';
import type { Stock, SortOrder } from '../types/stock';
import { getStockList } from '../services/stockService';

interface UseStockDataResult {
  stocks: Stock[];
  loading: boolean;
  error: string | null;
  sortOrder: SortOrder;
  setSortOrder: (order: SortOrder) => void;
  refetch: () => Promise<void>;
}

export function useStockData(codes: string[]): UseStockDataResult {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  const fetchData = useCallback(async () => {
    if (codes.length === 0) {
      setStocks([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await getStockList(codes);
      if (response.data) {
        setStocks(response.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [codes.join(',')]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 根据排序规则排序股票
  const sortedStocks = [...stocks].sort((a, b) => {
    const diff = a.changePercent - b.changePercent;
    return sortOrder === 'asc' ? diff : -diff;
  });

  return {
    stocks: sortedStocks,
    loading,
    error,
    sortOrder,
    setSortOrder,
    refetch: fetchData,
  };
}

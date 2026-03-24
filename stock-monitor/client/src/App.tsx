import { useState, useCallback } from 'react';
import { StockList } from './components/StockList';
import { useStockData } from './hooks/useStockData';
import type { SortOrder } from './types/stock';
import './App.css';

// 初始关注的股票列表
const DEFAULT_STOCK_CODES = [
  'sh600000',  // 浦发银行
  'sh600036',  // 招商银行
  'sh600519',  // 贵州茅台
  'sz000001',  // 平安银行
  'sz000002',  // 万科A
  'sz300750',  // 宁德时代
];

function App() {
  const [codes] = useState<string[]>(DEFAULT_STOCK_CODES);
  const { stocks, loading, error, sortOrder, setSortOrder, refetch } = useStockData(codes);

  const handleSortChange = useCallback((order: SortOrder) => {
    setSortOrder(order);
  }, [setSortOrder]);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  return (
    <StockList
      stocks={stocks}
      loading={loading}
      error={error}
      sortOrder={sortOrder}
      onSortChange={handleSortChange}
      onRefresh={handleRefresh}
    />
  );
}

export default App;

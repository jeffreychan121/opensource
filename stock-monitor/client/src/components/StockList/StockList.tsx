import React from 'react';
import type { Stock, SortOrder } from '../../types/stock';
import './StockList.css';

interface StockListProps {
  stocks: Stock[];
  loading: boolean;
  error: string | null;
  sortOrder: SortOrder;
  onSortChange: (order: SortOrder) => void;
  onRefresh: () => void;
}

function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万';
  }
  return num.toString();
}

function getPriceClass(change: number): string {
  if (change > 0) return 'stock-up';
  if (change < 0) return 'stock-down';
  return 'stock-neutral';
}

export const StockList: React.FC<StockListProps> = ({
  stocks,
  loading,
  error,
  sortOrder,
  onSortChange,
  onRefresh,
}) => {
  if (loading) {
    return (
      <div className="stock-list">
        <div className="loading-container">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stock-list">
        <div className="error-container">
          <p>加载失败: {error}</p>
          <button className="sort-btn" onClick={onRefresh}>
            重试
          </button>
        </div>
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="stock-list">
        <div className="empty-container">
          <p>暂无股票数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-list">
      <div className="stock-list-header">
        <h1 className="stock-list-title">股票行情监控</h1>
        <div>
          <button
            className={`sort-btn ${sortOrder === 'asc' ? 'active' : ''}`}
            onClick={() => onSortChange('asc')}
          >
            涨幅升序
          </button>
          <button
            className={`sort-btn ${sortOrder === 'desc' ? 'active' : ''}`}
            onClick={() => onSortChange('desc')}
            style={{ marginLeft: '8px' }}
          >
            涨幅降序
          </button>
        </div>
      </div>

      <table className="stock-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>当前价</th>
            <th>涨跌额</th>
            <th>涨跌幅</th>
            <th>成交量(手)</th>
            <th>成交额(万)</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={stock.code}>
              <td>
                <span className="stock-code">{stock.code}</span>
              </td>
              <td>
                <span className="stock-name">{stock.name}</span>
              </td>
              <td>
                <span className="stock-price">
                  {stock.price.toFixed(2)}
                </span>
              </td>
              <td className={getPriceClass(stock.change)}>
                {stock.change > 0 ? '+' : ''}
                {stock.change.toFixed(2)}
              </td>
              <td className={getPriceClass(stock.changePercent)}>
                {stock.changePercent > 0 ? '+' : ''}
                {stock.changePercent.toFixed(2)}%
              </td>
              <td>{formatNumber(stock.volume)}</td>
              <td>{formatNumber(stock.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

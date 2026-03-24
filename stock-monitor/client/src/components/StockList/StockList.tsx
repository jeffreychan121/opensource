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

interface StockCardProps {
  stock: Stock;
}

const StockCard: React.FC<StockCardProps> = ({ stock }) => {
  const priceClass = getPriceClass(stock.change);
  const isUp = stock.change > 0;
  const isDown = stock.change < 0;

  return (
    <div className="stock-card">
      <div className="stock-card-header">
        <div className="stock-info">
          <span className="stock-code">{stock.code}</span>
          <span className="stock-name">{stock.name}</span>
        </div>
        <div className={`stock-change-badge ${priceClass}`}>
          {stock.changePercent > 0 ? '+' : ''}
          {stock.changePercent.toFixed(2)}%
        </div>
      </div>

      <div className="stock-card-body">
        <div className="stock-price-section">
          <span className={`stock-price ${priceClass}`}>
            {stock.price.toFixed(2)}
          </span>
          <span className={`stock-change ${priceClass}`}>
            {stock.change > 0 ? '+' : ''}{stock.change.toFixed(2)}
          </span>
        </div>

        <div className="stock-details">
          <div className="stock-detail">
            <span className="detail-label">开盘</span>
            <span className="detail-value">{stock.open.toFixed(2)}</span>
          </div>
          <div className="stock-detail">
            <span className="detail-label">最高</span>
            <span className="detail-value">{stock.high.toFixed(2)}</span>
          </div>
          <div className="stock-detail">
            <span className="detail-label">最低</span>
            <span className="detail-value">{stock.low.toFixed(2)}</span>
          </div>
        </div>

        <div className="stock-stats">
          <div className="stock-stat">
            <span className="stat-label">成交量</span>
            <span className="stat-value">{formatNumber(stock.volume)}</span>
          </div>
          <div className="stock-stat">
            <span className="stat-label">成交额</span>
            <span className="stat-value">{formatNumber(stock.amount)}万</span>
          </div>
        </div>
      </div>

      <div className="stock-card-footer">
        <div className={`trend-indicator ${isUp ? 'up' : isDown ? 'down' : 'neutral'}`}>
          <span className="trend-arrow">{isUp ? '↑' : isDown ? '↓' : '─'}</span>
          <span className="trend-text">
            {isUp ? '上涨' : isDown ? '下跌' : '持平'}
          </span>
        </div>
      </div>
    </div>
  );
};

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
        <div className="header-actions">
          <button
            className={`sort-btn ${sortOrder === 'asc' ? 'active' : ''}`}
            onClick={() => onSortChange('asc')}
          >
            涨幅升序
          </button>
          <button
            className={`sort-btn ${sortOrder === 'desc' ? 'active' : ''}`}
            onClick={() => onSortChange('desc')}
          >
            涨幅降序
          </button>
        </div>
      </div>

      <div className="stock-card-grid">
        {stocks.map((stock) => (
          <StockCard key={stock.code} stock={stock} />
        ))}
      </div>
    </div>
  );
};

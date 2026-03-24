# Stock Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个股票行情监控Web应用，实现股票列表实时行情展示，支持按涨跌幅排序

**Architecture:** 前后端分离架构，前端React + TypeScript，后端Express.js代理新浪财经API

**Tech Stack:** React 18.x, TypeScript 5.x, Vite 5.x, Express.js 4.x, Axios

---

## Task 1: 初始化项目结构

**Files:**
- Create: `stock-monitor/client/package.json`
- Create: `stock-monitor/client/tsconfig.json`
- Create: `stock-monitor/client/vite.config.ts`
- Create: `stock-monitor/client/index.html`
- Create: `stock-monitor/server/package.json`

- [ ] **Step 1: 创建前端项目目录和配置文件**

```bash
mkdir -p stock-monitor/client/src
mkdir -p stock-monitor/server
```

创建 `stock-monitor/client/package.json`:
```json
{
  "name": "stock-monitor-client",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

创建 `stock-monitor/client/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

创建 `stock-monitor/client/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

创建 `stock-monitor/client/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true
      }
    }
  }
})
```

创建 `stock-monitor/client/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>股票行情监控</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 创建后端配置文件**

创建 `stock-monitor/server/package.json`:
```json
{
  "name": "stock-monitor-server",
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "start": "node index.js",
    "dev": "node --watch index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "axios": "^1.6.0"
  }
}
```

- [ ] **Step 3: 提交代码**

```bash
git add stock-monitor/
git commit -m "chore: 初始化stock-monitor项目结构"
```

---

## Task 2: 后端API开发

**Files:**
- Create: `stock-monitor/server/index.js`
- Create: `stock-monitor/server/utils/stockParser.js`

- [ ] **Step 1: 创建后端入口文件**

创建 `stock-monitor/server/index.js`:
```javascript
import express from 'express';
import cors from 'cors';
import axios from 'axios';

const app = express();
const PORT = 4000;

app.use(cors());
app.use(express.json());

// 股票代码映射表（简化的A股常用股票）
const STOCK_NAMES = {
  'sh600000': '浦发银行',
  'sh600036': '招商银行',
  'sh600519': '贵州茅台',
  'sh000001': '上证指数',
  'sz000001': '平安银行',
  'sz000002': '万科A',
  'sz300750': '宁德时代'
};

// 解析新浪财经返回的股票数据
function parseSinaStockData(data, code) {
  if (!data || data.length === 0) {
    return null;
  }

  // 新浪返回格式: var hq_str_sh600000="浦发银行,10.50,...";
  const match = data.match(/"([^"]+)"/);
  if (!match) {
    return null;
  }

  const fields = match[1].split(',');
  if (fields.length < 8) {
    return null;
  }

  const name = fields[0];
  const open = parseFloat(fields[1]) || 0;
  const close = parseFloat(fields[2]) || 0;
  const current = parseFloat(fields[3]) || 0;
  const high = parseFloat(fields[4]) || 0;
  const low = parseFloat(fields[5]) || 0;
  const volume = parseInt(fields[8]) || 0;
  const amount = parseFloat(fields[9]) || 0;

  const change = current - close;
  const changePercent = close > 0 ? (change / close) * 100 : 0;

  return {
    code,
    name: STOCK_NAMES[code] || name,
    price: current,
    open,
    high,
    low,
    close,
    change: change,
    changePercent: parseFloat(changePercent.toFixed(2)),
    volume: Math.floor(volume / 100), // 转换为手
    amount: Math.floor(amount / 10000) // 转换为万元
  };
}

// 获取股票数据API
app.get('/api/stocks', async (req, res) => {
  try {
    const { codes } = req.query;

    if (!codes) {
      return res.status(400).json({
        error: 'MISSING_CODES',
        message: '缺少股票代码参数'
      });
    }

    const codeList = codes.split(',').filter(c => c.trim());

    if (codeList.length === 0) {
      return res.status(400).json({
        error: 'INVALID_CODES',
        message: '股票代码不能为空'
      });
    }

    // 限制最多查询20只股票
    const limitedCodes = codeList.slice(0, 20);

    // 批量请求新浪财经API
    const results = await Promise.all(
      limitedCodes.map(async (code) => {
        try {
          const url = `http://hq.sinajs.cn/list=${code}`;
          const response = await axios.get(url, {
            timeout: 5000,
            headers: {
              'Referer': 'http://finance.sina.com.cn'
            }
          });
          return parseSinaStockData(response.data, code);
        } catch (error) {
          console.error(`获取股票 ${code} 失败:`, error.message);
          return null;
        }
      })
    );

    // 过滤掉失败的股票
    const validStocks = results.filter(s => s !== null);

    if (validStocks.length === 0) {
      return res.status(502).json({
        error: 'NO_DATA',
        message: '无法获取股票数据'
      });
    }

    res.json({ data: validStocks });

  } catch (error) {
    console.error('API错误:', error);
    res.status(500).json({
      error: 'SERVER_ERROR',
      message: '服务器内部错误'
    });
  }
});

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`Stock monitor server running on http://localhost:${PORT}`);
});
```

- [ ] **Step 2: 测试后端API**

```bash
cd stock-monitor/server
npm install
npm start &
```

测试API:
```bash
curl "http://localhost:4000/api/stocks?codes=sh600000,sh600519"
```

预期返回JSON数据

- [ ] **Step 3: 提交代码**

```bash
git add stock-monitor/server/
git commit -m "feat: 实现后端股票数据API"
```

---

## Task 3: 前端类型定义

**Files:**
- Create: `stock-monitor/client/src/types/stock.ts`
- Create: `stock-monitor/client/src/services/stockService.ts`

- [ ] **Step 1: 创建类型定义**

创建 `stock-monitor/client/src/types/stock.ts`:
```typescript
export interface Stock {
  code: string;
  name: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  change: number;
  changePercent: number;
  volume: number;
  amount: number;
}

export interface StockListResponse {
  data: Stock[];
  error?: string;
  message?: string;
}

export type SortOrder = 'asc' | 'desc';

export interface StockListProps {
  codes: string[];
}
```

- [ ] **Step 2: 创建API服务**

创建 `stock-monitor/client/src/services/stockService.ts`:
```typescript
import axios from 'axios';
import type { StockListResponse } from '../types/stock';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export async function getStockList(codes: string[]): Promise<StockListResponse> {
  const response = await api.get<StockListResponse>('/stocks', {
    params: { codes: codes.join(',') },
  });
  return response.data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await api.get('/health');
    return response.data.status === 'ok';
  } catch {
    return false;
  }
}
```

- [ ] **Step 3: 提交代码**

```bash
git add stock-monitor/client/src/
git commit -m "feat: 添加前端类型定义和API服务"
```

---

## Task 4: 自定义Hooks开发

**Files:**
- Create: `stock-monitor/client/src/hooks/useStockData.ts`

- [ ] **Step 1: 创建useStockData Hook**

创建 `stock-monitor/client/src/hooks/useStockData.ts`:
```typescript
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
```

- [ ] **Step 2: 提交代码**

```bash
git add stock-monitor/client/src/hooks/
git commit -m "feat: 添加useStockData自定义Hook"
```

---

## Task 5: 股票列表组件开发

**Files:**
- Create: `stock-monitor/client/src/components/StockList/StockList.tsx`
- Create: `stock-monitor/client/src/components/StockList/StockList.css`
- Create: `stock-monitor/client/src/components/StockList/index.ts`

- [ ] **Step 1: 创建股票列表组件样式**

创建 `stock-monitor/client/src/components/StockList/StockList.css`:
```css
.stock-list {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.stock-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stock-list-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.sort-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.sort-btn:hover {
  background: #f5f5f5;
}

.sort-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stock-table th,
.stock-table td {
  padding: 12px 16px;
  text-align: left;
}

.stock-table th {
  background: #fafafa;
  font-weight: 600;
  color: #666;
  font-size: 14px;
}

.stock-table td {
  border-top: 1px solid #f0f0f0;
  font-size: 14px;
}

.stock-code {
  font-weight: 500;
  color: #333;
}

.stock-name {
  color: #666;
  margin-left: 8px;
}

.stock-price {
  font-weight: 600;
  font-size: 16px;
}

.stock-up {
  color: #ff0000;
}

.stock-down {
  color: #00ff00;
}

.stock-neutral {
  color: #999;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  padding: 40px;
  text-align: center;
  color: #ff4d4f;
}

.empty-container {
  padding: 40px;
  text-align: center;
  color: #999;
}
```

- [ ] **Step 2: 创建股票列表组件**

创建 `stock-monitor/client/src/components/StockList/StockList.tsx`:
```typescript
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
```

创建 `stock-monitor/client/src/components/StockList/index.ts`:
```typescript
export { StockList } from './StockList';
```

- [ ] **Step 3: 提交代码**

```bash
git add stock-monitor/client/src/components/
git commit -m "feat: 添加股票列表组件"
```

---

## Task 6: 主应用组件

**Files:**
- Create: `stock-monitor/client/src/App.tsx`
- Create: `stock-monitor/client/src/App.css`
- Create: `stock-monitor/client/src/main.tsx`

- [ ] **Step 1: 创建主应用样式**

创建 `stock-monitor/client/src/App.css`:
```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #f5f5f5;
}

#root {
  min-height: 100vh;
}
```

- [ ] **Step 2: 创建主应用组件**

创建 `stock-monitor/client/src/App.tsx`:
```typescript
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
```

创建 `stock-monitor/client/src/main.tsx`:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 3: 提交代码**

```bash
git add stock-monitor/client/src/
git commit -m "feat: 添加主应用入口组件"
```

---

## Task 7: 安装依赖并验证

**Files:**
- Modify: `stock-monitor/client/package.json` (安装依赖)
- Modify: `stock-monitor/server/package.json` (安装依赖)

- [ ] **Step 1: 安装前端依赖**

```bash
cd stock-monitor/client
npm install
```

- [ ] **Step 2: 启动后端服务**

```bash
cd stock-monitor/server
npm install
node index.js &
```

- [ ] **Step 3: 启动前端并验证**

```bash
cd stock-monitor/client
npm run dev
```

访问 http://localhost:3000 验证页面是否正常显示

- [ ] **Step 4: 提交最终版本**

```bash
git add stock-monitor/
git commit -m "feat: stock-monitor项目完成"
```

---

## 验收标准

1. ✅ 后端服务启动成功，可访问 http://localhost:4000
2. ✅ 前端页面启动成功，可访问 http://localhost:3000
3. ✅ 股票列表正确显示6只股票的实时数据
4. ✅ 点击排序按钮可以切换升序/降序
5. ✅ 上涨显示红色，下跌显示绿色
6. ✅ 加载状态显示loading动画
7. ✅ 错误状态显示错误信息

---

## 后续扩展

- 添加股票搜索功能
- 支持自选股管理（本地存储）
- 添加K线图表展示
- 定时自动刷新数据
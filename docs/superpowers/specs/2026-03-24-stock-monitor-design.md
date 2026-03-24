# 股票行情监控工具 - 设计文档

## 1. 项目概述

- **项目名称**: stock-monitor
- **项目类型**: 个人投资工具（Web应用）
- **核心功能**: 股票列表实时行情展示，支持按涨跌幅排序
- **目标用户**: 个人投资者

## 2. 技术栈

| 层级 | 技术选型 | 版本 |
|------|----------|------|
| 前端框架 | React | 18.x |
| 语言 | TypeScript | 5.x |
| 构建工具 | Vite | 5.x |
| 后端 | Express.js | 4.x |
| HTTP客户端 | Axios | 1.x |
| 样式方案 | CSS Modules | - |

## 3. 项目结构

```
stock-monitor/
├── client/                    # 前端项目
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   └── StockList/     # 股票列表组件
│   │   ├── services/          # API服务
│   │   ├── types/             # TypeScript类型定义
│   │   ├── hooks/             # 自定义Hooks
│   │   ├── App.tsx            # 主应用组件
│   │   ├── App.css            # 全局样式
│   │   └── main.tsx           # 入口文件
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── server/                    # 后端项目
│   ├── index.js               # Express服务入口
│   └── package.json
└── README.md
```

## 4. 功能需求

### 4.1 股票列表

- 显示多只股票的实时行情数据
- 数据字段：
  - 股票代码（如 600000）
  - 股票名称（如 浦发银行）
  - 当前价格
  - 涨跌幅（百分比）
  - 涨跌额（绝对值）
  - 成交量（手）
  - 成交额（金额）

### 4.2 排序功能

- 支持按涨跌幅排序
- 支持升序/降序切换

### 4.3 颜色规则

- 上涨：红色 (#FF0000)
- 下跌：绿色 (#00FF00)

### 4.4 数据刷新

- 页面加载时获取数据
- 可扩展：定时刷新（后续功能）

## 5. API设计

### 5.1 后端接口

**GET /api/stocks**
- 参数：`codes` - 股票代码列表，用逗号分隔
- 示例：`/api/stocks?codes=sh600000,sz000001`
- 响应：
```json
{
  "data": [
    {
      "code": "sh600000",
      "name": "浦发银行",
      "price": 10.50,
      "change": 0.15,
      "changePercent": 1.45,
      "volume": 1234567,
      "amount": 123456789
    }
  ]
}
```

### 5.2 数据源

- 新浪财经股票接口
- 接口地址：`http://hq.sinajs.cn/list={code}`
- 需要通过后端代理解决跨域

## 6. 组件设计

### 6.1 StockList 组件

- **职责**：获取并展示股票列表数据
- **输入**：股票代码列表
- **输出**：渲染股票行情表格

### 6.2 数据流

```
App.tsx
  └── StockList
        └── useStockData (自定义Hook)
              └── stockService.getStocks()
                    └── Axios → 后端 /api/stocks
                          └── Express → 新浪财经API
```

## 7. 验收标准

1. ✅ 前端能够正常启动并显示页面
2. ✅ 后端能够返回股票数据
3. ✅ 股票列表正确显示所有字段
4. ✅ 涨跌幅排序功能正常
5. ✅ 上涨显示红色，下跌显示绿色
6. ✅ 跨域问题已解决

## 8. 后续扩展

- K线图表
- 股票搜索
- 自选股管理
- 实时数据推送
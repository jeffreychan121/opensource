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

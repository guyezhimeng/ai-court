import { useEffect, useState } from 'react';
import { Newspaper, ExternalLink, Clock, RefreshCw, TrendingUp, Globe } from 'lucide-react';
import { api } from '@/api';

interface NewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  category: string;
  url: string;
  created_at: string;
}

const MOCK_NEWS: NewsItem[] = [
  {
    id: '1',
    title: 'DeepSeek-V3 发布，推理能力大幅提升',
    summary: 'DeepSeek 发布最新 V3 模型，在代码生成、数学推理和多轮对话方面取得显著进步，API 价格保持不变。',
    source: 'AI 日报',
    category: '模型',
    url: '#',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: '2',
    title: 'OpenAI 推出 GPT-4.1 系列',
    summary: 'GPT-4.1、GPT-4.1 mini 和 GPT-4.1 nano 三个版本，在指令遵循和长上下文理解方面有重大改进。',
    source: '科技要闻',
    category: '模型',
    url: '#',
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: '3',
    title: '阿里云百炼平台全面升级',
    summary: '新增模型微调、RAG 知识库和企业级安全功能，通义千问系列模型性能提升 30%。',
    source: '云服务',
    category: '平台',
    url: '#',
    created_at: new Date(Date.now() - 14400000).toISOString(),
  },
  {
    id: '4',
    title: 'Claude 3.5 Sonnet 新版发布',
    summary: 'Anthropic 发布 Claude 3.5 Sonnet 更新版，在编码和视觉理解方面超越前代。',
    source: 'AI 日报',
    category: '模型',
    url: '#',
    created_at: new Date(Date.now() - 28800000).toISOString(),
  },
  {
    id: '5',
    title: 'Docker Desktop 4.30 发布',
    summary: '新增 WSL2 性能优化和容器镜像加速功能，构建速度提升 40%。',
    source: '开发工具',
    category: '工具',
    url: '#',
    created_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: '6',
    title: '智谱 GLM-4 开放 API',
    summary: 'GLM-4 系列模型全面开放 API 接口，支持 128K 上下文，价格低于行业平均水平。',
    source: '国产模型',
    category: '模型',
    url: '#',
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
];

const CATEGORIES = ['全部', '模型', '平台', '工具'];

export function NewsPanel() {
  const [news, setNews] = useState<NewsItem[]>(MOCK_NEWS);
  const [category, setCategory] = useState('全部');
  const [loading, setLoading] = useState(false);

  const filteredNews = category === '全部' ? news : news.filter((n) => n.category === category);

  const relTime = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}小时前`;
    return `${Math.floor(hours / 24)}天前`;
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-5xl mx-auto animate-fadeIn">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title text-xl mb-0">
          <span className="text-court-acc">📰</span> 天下要闻
        </h2>
        <button className="btn-ghost btn-sm flex items-center gap-1.5">
          <RefreshCw size={14} /> 刷新
        </button>
      </div>

      <div className="theme-card-static mb-6 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Globe size={16} className="text-court-acc" />
          <span className="text-sm font-medium text-court-text">AI 行业动态</span>
        </div>
        <p className="text-xs text-court-muted">
          汇聚大模型、云平台、开发工具等领域的最新动态，助朝廷决策者洞察先机。
        </p>
      </div>

      <div className="flex gap-1 mb-4">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={category === cat ? 'filter-btn-active' : 'filter-btn'}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filteredNews.map((item) => (
          <div key={item.id} className="theme-card group">
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="status-badge bg-court-acc/15 text-court-acc text-[10px]">{item.category}</span>
                  <span className="text-[10px] text-court-muted">{item.source}</span>
                  <span className="text-[10px] text-court-muted ml-auto flex items-center gap-1">
                    <Clock size={10} /> {relTime(item.created_at)}
                  </span>
                </div>
                <h3 className="text-sm font-medium text-court-text mb-1 group-hover:text-court-acc transition-colors">
                  {item.title}
                </h3>
                <p className="text-xs text-court-muted line-clamp-2">{item.summary}</p>
              </div>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-court-panel2 text-court-muted hover:text-court-acc transition-colors shrink-0"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink size={14} />
              </a>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 text-center text-xs text-court-muted">
        <TrendingUp size={14} className="inline mr-1" />
        数据来源于公开信息，仅供参考
      </div>
    </div>
  );
}

<!-- 管理后台首页：统计卡片 + 提问趋势折线图 + 文档分布饼图 + 活跃用户柱状图 -->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { statsApi } from '@/api'
import ChartCard from '@/components/ChartCard.vue'

/** 主色调，各图表统一使用 */
const PRIMARY = '#409eff'

const overview = ref({ user_count: 0, kb_count: 0, doc_count: 0, question_count: 0, today_question_count: 0 })
const trend = ref<{ dates: string[]; counts: number[] }>({ dates: [], counts: [] })
const distribution = ref<{ name: string; value: number }[]>([])
const activeUsers = ref<{ names: string[]; counts: number[] }>({ names: [], counts: [] })

/** 顶部统计卡片 */
const cards = computed(() => [
  { label: '用户总数', value: overview.value.user_count, icon: 'User', color: '#409eff' },
  { label: '知识库', value: overview.value.kb_count, icon: 'Collection', color: '#67c23a' },
  { label: '文档数量', value: overview.value.doc_count, icon: 'Document', color: '#e6a23c' },
  {
    label: '累计提问',
    value: overview.value.question_count,
    icon: 'ChatDotRound',
    color: '#8e7cc3',
    extra: `今日 ${overview.value.today_question_count}`,
  },
])

/** 近 7 天提问趋势折线图 */
const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: trend.value.dates, boundaryGap: false },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      name: '提问数',
      type: 'line',
      smooth: true,
      data: trend.value.counts,
      itemStyle: { color: PRIMARY },
      areaStyle: { color: 'rgba(64, 158, 255, 0.15)' },
    },
  ],
}))

/** 知识库文档分布饼图 */
const pieOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item', formatter: '{b}：{c} 篇（{d}%）' },
  legend: { bottom: 0 },
  color: ['#409eff', '#67c23a', '#e6a23c', '#8e7cc3', '#f56c6c', '#909399'],
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{c} 篇' },
      data: distribution.value,
    },
  ],
}))

/** 活跃用户 Top5 柱状图（横向，名字较长时更易读） */
const barOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 60, right: 30, top: 10, bottom: 30 },
  xAxis: { type: 'value', minInterval: 1 },
  // 倒序让第一名显示在最上方
  yAxis: { type: 'category', data: [...activeUsers.value.names].reverse() },
  series: [
    {
      name: '提问数',
      type: 'bar',
      barWidth: 18,
      data: [...activeUsers.value.counts].reverse(),
      itemStyle: { color: PRIMARY, borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right' },
    },
  ],
}))

/** 并行加载全部统计数据 */
async function loadData() {
  const [o, t, d, a] = await Promise.all([
    statsApi.overview(),
    statsApi.trend(),
    statsApi.docDistribution(),
    statsApi.activeUsers(),
  ])
  overview.value = o
  trend.value = t
  distribution.value = d
  activeUsers.value = a
}

onMounted(loadData)
</script>
<template>
  <div>
    <el-row :gutter="20">
      <el-col v-for="c in cards" :key="c.label" :span="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: c.color }">
            <el-icon :size="26" color="#fff"><component :is="c.icon" /></el-icon>
          </div>
          <div>
            <div class="stat-value">{{ c.value }}</div>
            <div class="stat-label">
              {{ c.label }}
              <span v-if="c.extra" class="stat-extra">{{ c.extra }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <ChartCard title="近 7 天提问趋势" :option="trendOption" />
      </el-col>
      <el-col :span="8">
        <ChartCard title="知识库文档分布" :option="pieOption" />
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="24">
        <ChartCard title="活跃用户 Top5" :option="barOption" height="240px" />
      </el-col>
    </el-row>
  </div>
</template>
<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 26px;
  font-weight: 600;
  line-height: 1.2;
}

.stat-label {
  color: #909399;
  margin-top: 4px;
}

.stat-extra {
  margin-left: 6px;
  font-size: 12px;
  color: #67c23a;
}

.chart-row {
  margin-top: 20px;
}
</style>
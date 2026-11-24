<!-- ECharts 图表卡片：传入 title 和 option 即可渲染，窗口缩放时自动调整大小 -->
<script lang="ts" setup name="ChartCard">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
const props = defineProps<{
  /** 卡片标题 */
  title: string
  /** ECharts 配置项 */
  option: echarts.EChartsOption
  /** 图表高度 */
  height?: string
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

onMounted(() => {
  chart = echarts.init(chartRef.value!)
  chart.setOption(props.option)
  // 监听容器尺寸变化（比窗口 resize 更准确，侧边栏折叠时也能触发）
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(chartRef.value!)
})

// 数据变化时重新渲染
watch(
  () => props.option,
  (opt) => chart?.setOption(opt, true),
  { deep: true },
)

// 组件销毁时释放图表实例，防止内存泄漏
onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>
<template>
  <div class="chart-card">
    <div class="chart-title">{{ title }}</div>
    <div ref="chartRef" :style="{ height: height ?? '300px' }" role="img" :aria-label="title" />
  </div>
</template>
<style scoped>
.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
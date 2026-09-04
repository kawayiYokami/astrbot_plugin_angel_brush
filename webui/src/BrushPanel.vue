<template>
  <n-layout class="layout" has-sider>
    <!-- 可变式侧边栏 -->
    <n-layout-sider
      width="240"
      collapse-mode="width"
      :collapsed-width="56"
      show-trigger="bar"
      :collapsed="collapsed"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="sider-inner" :class="{ collapsed }">
        <div class="sider-header">
          <button
            class="theme-toggle"
            type="button"
            :title="isDark ? '切换到光模式' : '切换到暗模式'"
            @click="toggleTheme()"
          >
            <Icon :icon="isDark ? 'lucide:sun' : 'lucide:moon'" />
          </button>
          <div v-if="!collapsed" class="brand">天使的画笔</div>
        </div>
        <n-scrollbar class="sider-scroll">
          <n-menu
            :value="activeKey"
            :options="menuOptions"
            :collapsed="collapsed"
            :collapsed-width="56"
            :collapsed-icon-size="20"
            @update:value="onMenu"
          />
        </n-scrollbar>
        <div v-if="!collapsed" class="sider-footer">
          <span class="foot-hint">angel_image_generate / angel_image_edit</span>
        </div>
      </div>
    </n-layout-sider>

    <n-layout-content class="content">
      <n-scrollbar class="content-scroll">
        <div class="content-inner">
          <!-- 供应商设置 -->
          <template v-if="activeKey === 'providers'">
            <div class="content-header">
              <h2>供应商设置</h2>
              <div class="header-actions">
                <n-button @click="reload">
                  <template #icon><Icon icon="lucide:refresh-cw" /></template>
                  刷新
                </n-button>
                <n-button type="primary" @click="addProvider">
                  <template #icon><Icon icon="lucide:plus" /></template>
                  供应商
                </n-button>
              </div>
            </div>
            <p class="content-sub">6 家协议 openai / xai / seedream / gemini / sensenova / comfyui，保存后即时生效</p>

            <n-spin v-if="loading" style="margin-top: 40px" />

            <template v-else>
              <n-empty v-if="!providers.length" description="还没有供应商，点击右上角新增" style="margin-top: 30px" />

              <div v-for="(p, pIdx) in providers" :key="p.id" class="provider-card">
                <div class="provider-head">
                  <div class="provider-title">
                    <Icon icon="lucide:server" class="inline-icon" />
                    <span class="provider-name">{{ p.name || '未命名供应商' }}</span>
                    <n-tag type="info">{{ p.provider_type }}</n-tag>
                  </div>
                  <div class="provider-actions">
                    <n-switch v-model:value="p.enabled" />
                    <n-popconfirm @positive-click="removeProvider(pIdx)">
                      <template #trigger>
                        <n-button quaternary circle type="error" title="删除供应商">
                          <template #icon><Icon icon="lucide:trash-2" /></template>
                        </n-button>
                      </template>
                      删除 {{ p.name || p.id }}？此操作需保存后生效
                    </n-popconfirm>
                  </div>
                </div>

                <n-grid :cols="2" :x-gap="12" :y-gap="10" responsive="screen" collapsed-rows="1">
                  <n-gi>
                    <n-form-item label="名称" :show-feedback="false" style="margin-bottom: 0">
                      <n-input v-model:value="p.name" placeholder="如：OpenAI Images" />
                    </n-form-item>
                  </n-gi>
                  <n-gi>
                    <n-form-item label="类型" :show-feedback="false" style="margin-bottom: 0">
                      <n-select v-model:value="p.provider_type" :options="kindOptions" />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="2">
                    <n-form-item label="Base URL" :show-feedback="false" style="margin-bottom: 0">
                      <n-input v-model:value="p.base_url" placeholder="https://api.openai.com/v1" />
                    </n-form-item>
                  </n-gi>
                  <n-gi>
                    <n-form-item label="超时 (秒)" :show-feedback="false" style="margin-bottom: 0">
                      <n-input-number v-model:value="p.timeout_seconds" :min="10" :max="600" :show-button="false" style="width: 140px" />
                    </n-form-item>
                  </n-gi>
                  <n-gi>
                    <n-form-item label="水印" :show-feedback="false" style="margin-bottom: 0">
                      <n-switch v-model:value="p.watermark" />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="2">
                    <n-form-item label="API Keys" :show-feedback="false" style="margin-bottom: 0">
                      <div class="key-row">
                        <n-tag
                          v-for="(k, ki) in p.api_keys"
                          :key="ki"
                         
                          :bordered="false"
                          closable
                          @close="p.api_keys.splice(ki, 1)"
                        >
                          {{ maskKey(k) }}
                        </n-tag>
                        <n-input
                          v-model:value="keyInput[p.id]"
                          placeholder="sk-... 回车添加"
                          style="width: 220px"
                          clearable
                          @keyup.enter="addKey(p)"
                        />
                      </div>
                    </n-form-item>
                    <div class="hint">支持多 key 轮询，空则不鉴权</div>
                  </n-gi>
                  <template v-if="p.provider_type === 'comfyui'">
                    <n-gi :span="2">
                      <n-form-item label="ComfyUI Workflow JSON" :show-feedback="false" style="margin-bottom: 0">
                        <n-input v-model:value="p.comfyui_workflow_json" type="textarea" :autosize="{ minRows: 3 }" placeholder='{"prompt":...}' />
                      </n-form-item>
                    </n-gi>
                  </template>
                </n-grid>

                <div class="models-head">
                  <span class="models-title"><Icon icon="lucide:layers" class="inline-icon" /> 模型 ({{ p.models.length }})</span>
                  <n-button size="tiny" @click="addModel(p)">
                    <template #icon><Icon icon="lucide:plus" /></template>
                    模型
                  </n-button>
                </div>

                <div v-if="!p.models.length" class="model-empty">该供应商还没有模型</div>
                <div v-for="(m, mIdx) in p.models" :key="m.id" class="model-card">
                  <div class="model-head">
                    <span class="model-name">{{ m.name || m.model }}</span>
                    <n-switch v-model:value="m.enabled" style="margin-left: auto" />
                    <n-popconfirm @positive-click="removeModel(p, mIdx)">
                      <template #trigger>
                        <n-button size="tiny" quaternary circle type="error">
                          <template #icon><Icon icon="lucide:x" /></template>
                        </n-button>
                      </template>
                      删除模型 {{ m.name || m.model }}？
                    </n-popconfirm>
                  </div>
                  <n-grid :cols="2" :x-gap="10" :y-gap="8">
                    <n-gi>
                      <n-form-item label="显示名" :show-feedback="false" style="margin-bottom: 0">
                        <n-input v-model:value="m.name" placeholder="如：GPT Image 1" />
                      </n-form-item>
                    </n-gi>
                    <n-gi>
                      <n-form-item label="模型名" :show-feedback="false" style="margin-bottom: 0">
                        <n-input
                          :value="m.model"
                          placeholder="如：gpt-image-1"
                         
                          @update:value="(v: string) => onModelNameChange(p, m, v)"
                        />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                </div>
              </div>

            </template>
          </template>

          <!-- 功能设置：仅保留生图模型供应商选择下拉 -->
          <template v-else-if="activeKey === 'settings'">
            <div class="content-header">
              <h2>功能设置</h2>
            </div>

            <n-spin v-if="loading" style="margin-top: 40px" />
            <template v-else>
              <n-card class="setting-card">
                <n-form label-placement="top">
                  <n-form-item label="生图模型">
                    <n-select
                      v-model:value="defaultModelId"
                      :options="modelOptions"
                      placeholder="请选择生图模型"
                      clearable
                     
                      @update:value="onDefaultModelChange"
                    />
                  </n-form-item>

                  <!-- 画风注入：勾选叠加，非互斥 -->
                  <n-divider style="margin-top: 16px" />
                  <div class="style-head">
                    <span class="style-title">画风注入（写入工具说明，LLM 每次调用可见）</span>
                  </div>
                  <n-form-item label="按模型推荐画风">
                    <n-checkbox v-model:checked="styleRecommend" @update:checked="onStyleChange">
                      使用当前模型擅长的画风
                    </n-checkbox>
                    <template #feedback>
                      <span v-if="defaultModelId && currentModelStyle" class="hint">{{ defaultModelId.split('::')[0] }} → {{ currentModelStyle }}</span>
                      <span v-else-if="defaultModelId && !currentModelStyle" class="hint warn">当前模型没有内置画风词条，仅勾选也不注入</span>
                      <span v-else class="hint">选择生图模型后，这里会显示该模型擅长的画风</span>
                    </template>
                  </n-form-item>
                  <n-form-item label="自定义画风">
                    <n-input
                      v-model:value="customStyle"
                      type="textarea"
                      :autosize="{ minRows: 1, maxRows: 3 }"
                      placeholder="如：多画赛璐璐动画风、色彩明亮干净，可叠加模型推荐一起生效"
                     
                      @update:value="onStyleChange"
                    />
                    <template #feedback>
                      <span class="hint">留空则不注入；与模型推荐可同时生效</span>
                    </template>
                  </n-form-item>
                </n-form>
                <n-alert v-if="!modelOptions.length" type="warning" :show-icon="false" style="margin-top: 10px">还没有可用模型，请先在供应商设置中添加并启用供应商与模型</n-alert>
                <div class="hint" style="margin-top: 8px">切换后自动保存并即时生效，无需再点右下角保存</div>
              </n-card>
            </template>
          </template>

          <!-- 工具测试：两工具全参数透传，编辑支持本地上传 -->
          <template v-else>
            <div class="content-header">
              <h2>工具测试</h2>
              <n-button @click="refreshGenerated">
                <template #icon><Icon icon="lucide:refresh-cw" /></template>
                刷新已生成
              </n-button>
            </div>
            <p class="content-sub">不依赖 LLM，直接调用本地调度与落盘链路。两工具全参数透传，编辑支持本地图片上传（转 data URL 直调）</p>

            <n-tabs type="line" animated :value="toolTab" @update:value="(v: string) => toolTab = v as any">
              <!-- 生图 -->
              <n-tab-pane name="generate" tab="angel_image_generate">
                <n-card class="setting-card">
                  <n-form label-placement="top">
                    <n-form-item label="生图模型（留空则用功能设置中的默认）">
                      <n-select v-model:value="genForm.model_id" :options="modelOptionsWithDefault" placeholder="默认模型" clearable />
                    </n-form-item>
                    <n-form-item label="prompt *">
                      <n-input v-model:value="genForm.prompt" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" placeholder="a cute cat sitting on a cloud, anime style" />
                    </n-form-item>
                    <n-form-item label="negative_prompt">
                      <n-input v-model:value="genForm.negative_prompt" type="textarea" :autosize="{ minRows: 1, maxRows: 3 }" placeholder="不希望出现的内容" />
                    </n-form-item>
                    <n-grid :cols="2" :x-gap="10" :y-gap="6">
                      <n-gi><n-form-item label="分辨率 (size / resolution)"><n-input v-model:value="genForm.size" placeholder="1024x1024" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="快捷尺寸"><n-select v-model:value="genForm.size" :options="resOptions" placeholder="选择预设" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="宽高比 (aspect_ratio)"><n-input v-model:value="genForm.aspect_ratio" placeholder="如 16:9 / 1:1" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="质量 (quality)"><n-input v-model:value="genForm.quality" placeholder="如 medium / high" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="数量 n (1-4)"><n-input-number v-model:value="genForm.n" :min="1" :max="4" style="width: 100%" /></n-form-item></n-gi>
                      <n-gi><n-form-item label="seed"><n-input v-model:value="genForm.seed" placeholder="留空随机" clearable /></n-form-item></n-gi>
                    </n-grid>
                  </n-form>
                  <div class="test-actions">
                    <n-button type="primary" :loading="genTesting" @click="doGenTest(true)">
                      <template #icon><Icon icon="lucide:flask-conical" /></template>
                      Mock 生成
                    </n-button>
                    <n-button :loading="genTesting" @click="doGenTest(false)">
                      <template #icon><Icon icon="lucide:sparkles" /></template>
                      真实生成
                    </n-button>
                    <span v-if="genMsg" class="hint">{{ genMsg }}</span>
                  </div>
                  <div v-if="genPreviews.length" class="test-previews">
                    <div v-for="(p, idx) in genPreviews" :key="idx" class="test-preview">
                      <img :src="p.src" alt="preview" />
                      <div v-if="p.markdown" class="preview-md">{{ p.markdown }}</div>
                    </div>
                  </div>
                </n-card>
              </n-tab-pane>

              <!-- 编辑 -->
              <n-tab-pane name="edit" tab="angel_image_edit">
                <n-card class="setting-card">
                  <n-form label-placement="top">
                    <n-form-item label="生图模型（留空则用默认）">
                      <n-select v-model:value="editForm.model_id" :options="modelOptionsWithDefault" placeholder="默认模型" clearable />
                    </n-form-item>
                    <n-form-item label="prompt *">
                      <n-input v-model:value="editForm.prompt" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" placeholder="把背景换成海边日落，保留主体" />
                    </n-form-item>
                    <n-form-item label="negative_prompt">
                      <n-input v-model:value="editForm.negative_prompt" type="textarea" :autosize="{ minRows: 1, maxRows: 3 }" placeholder="不希望出现的内容" />
                    </n-form-item>
                    <n-form-item label="输入图片 images *（可多选，支持多图融合）">
                      <div class="upload-area">
                        <input ref="editFileInput" type="file" accept="image/*" multiple style="display:none" @change="onEditFiles" />
                        <n-button @click="triggerEditPick">
                          <template #icon><Icon icon="lucide:upload" /></template>
                          选择图片
                        </n-button>
                        <span class="hint" style="margin-left:8px">{{ editImages.length }} 张已选（最多 16）</span>
                        <n-button v-if="editImages.length" size="tiny" quaternary style="margin-left:8px" @click="clearEditImages">清空</n-button>
                      </div>
                      <div v-if="editImages.length" class="upload-grid">
                        <div v-for="(it, idx) in editImages" :key="idx" class="upload-thumb">
                          <img :src="it.dataUrl" :alt="it.name" />
                          <div class="upload-thumb-bar">
                            <span class="upload-thumb-name" :title="it.name">{{ it.name }}</span>
                            <n-button size="tiny" quaternary circle type="error" @click="removeEditImage(idx)">
                              <template #icon><Icon icon="lucide:x" /></template>
                            </n-button>
                          </div>
                        </div>
                      </div>
                    </n-form-item>
                    <n-form-item label="mask（可选，白色区域为可编辑区）">
                      <div class="upload-area">
                        <input ref="maskFileInput" type="file" accept="image/*" style="display:none" @change="onMaskFile" />
                        <n-button @click="triggerMaskPick">
                          <template #icon><Icon icon="lucide:upload" /></template>
                          选择 mask
                        </n-button>
                        <span v-if="maskImage" class="hint" style="margin-left:8px">{{ maskImage.name }}</span>
                        <n-button v-if="maskImage" size="tiny" quaternary style="margin-left:8px" @click="clearMask">移除</n-button>
                      </div>
                      <div v-if="maskImage" class="upload-grid">
                        <div class="upload-thumb">
                          <img :src="maskImage.dataUrl" :alt="maskImage.name" />
                        </div>
                      </div>
                    </n-form-item>
                    <n-grid :cols="2" :x-gap="10" :y-gap="6">
                      <n-gi><n-form-item label="分辨率（最短边，不填按原图）"><n-input v-model:value="editForm.size" placeholder="如 1024" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="快捷分辨率"><n-select v-model:value="editForm.size" :options="editResOptions" placeholder="选择预设" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="宽高比（不填按原图）"><n-input v-model:value="editForm.aspect_ratio" placeholder="如 16:9 / 1:1" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="质量 (quality)"><n-input v-model:value="editForm.quality" placeholder="如 medium" clearable /></n-form-item></n-gi>
                      <n-gi><n-form-item label="seed"><n-input v-model:value="editForm.seed" placeholder="留空随机" clearable /></n-form-item></n-gi>
                    </n-grid>
                  </n-form>
                  <n-alert v-if="!editImages.length" type="warning" :show-icon="false" style="margin-top: 6px">请先上传至少一张输入图片</n-alert>
                  <div class="test-actions" style="margin-top: 10px">
                    <n-button type="primary" :loading="editTesting" @click="doEditTest(true)">
                      <template #icon><Icon icon="lucide:flask-conical" /></template>
                      Mock 编辑
                    </n-button>
                    <n-button :loading="editTesting" @click="doEditTest(false)">
                      <template #icon><Icon icon="lucide:sparkles" /></template>
                      真实编辑
                    </n-button>
                    <span v-if="editMsg" class="hint">{{ editMsg }}</span>
                  </div>
                  <div v-if="editPreviews.length" class="test-previews">
                    <div v-for="(p, idx) in editPreviews" :key="idx" class="test-preview">
                      <img :src="p.src" alt="preview" />
                      <div v-if="p.markdown" class="preview-md">{{ p.markdown }}</div>
                    </div>
                  </div>
                </n-card>
              </n-tab-pane>
            </n-tabs>

            <div class="gen-head">
              <span class="gen-title"><Icon icon="lucide:images" class="inline-icon" /> 已生成（最近 40 张）</span>
              <span class="hint">{{ generated.length }} 张</span>
            </div>
            <n-spin v-if="genLoading" />
            <n-empty v-else-if="!generated.length" description="还没有生成记录" />
            <div v-else class="img-grid">
              <div v-for="it in generated" :key="it.relative_path" class="img-card" @click="openImage(it)">
                <img v-if="thumbMap[it.relative_path]" :src="thumbMap[it.relative_path]" :alt="it.name" loading="lazy" />
                <div v-else class="img-placeholder"><Icon icon="lucide:image" /></div>
                <div class="img-cap">
                  <span class="img-name">{{ it.name }}</span>
                  <span class="img-date">{{ it.date }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </n-scrollbar>
    </n-layout-content>

    <!-- 悬浮保存 -->
    <Transition name="fab">
      <n-button
        v-if="dirty && activeKey !== 'tools'"
        class="save-fab"
        type="primary"
        round
        size="large"
        :loading="saving"
        @click="save"
      >
        <template #icon><Icon icon="lucide:save" /></template>
        保存更改
      </n-button>
    </Transition>

    <!-- 图片预览弹窗 -->
    <n-modal v-model:show="previewVisible" preset="card" :title="previewTitle" style="width: min(720px, 96vw)">
      <img v-if="previewSrc" :src="previewSrc" style="width: 100%; border-radius: 12px" />
      <div v-if="previewPath" class="hint" style="margin-top: 8px">{{ previewPath }}</div>
    </n-modal>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h, inject, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NCheckbox,
  NDivider,
  NEmpty,
  NForm,
  NFormItem,
  NGi,
  NGrid,
  NInput,
  NInputNumber,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NMenu,
  NModal,
  NPopconfirm,
  NScrollbar,
  NSelect,
  NSpin,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import { Icon } from '@iconify/vue'
import { useBridge } from './composables/useBridge'
import { themeKey } from './theme'

const { apiGet, apiPost, init } = useBridge()
const message = useMessage()
const { isDark, toggle: toggleTheme } = inject(themeKey)!

const collapsed = ref(false)
const activeKey = ref<'providers' | 'settings' | 'tools'>('providers')
const narrowMql = window.matchMedia('(max-width: 768px)')
const syncCollapsed = () => { collapsed.value = narrowMql.matches }
onMounted(() => {
  syncCollapsed()
  narrowMql.addEventListener('change', syncCollapsed)
})

const menuOptions: MenuOption[] = [
  { label: '供应商设置', key: 'providers', icon: () => h(Icon, { icon: 'lucide:server' }) },
  { label: '功能设置', key: 'settings', icon: () => h(Icon, { icon: 'lucide:settings' }) },
  { label: '工具测试', key: 'tools', icon: () => h(Icon, { icon: 'lucide:flask-conical' }) },
]
function onMenu(k: string) { activeKey.value = k as any; if (k === 'tools') refreshGenerated() }

const kindOptions = [
  { label: 'openai', value: 'openai' },
  { label: 'xai', value: 'xai' },
  { label: 'seedream', value: 'seedream' },
  { label: 'gemini', value: 'gemini' },
  { label: 'sensenova', value: 'sensenova' },
  { label: 'comfyui', value: 'comfyui' },
]
const resOptions = [
  { label: '512x512', value: '512x512' },
  { label: '1024x1024', value: '1024x1024' },
  { label: '1024x1536', value: '1024x1536' },
  { label: '1536x1024', value: '1536x1024' },
  { label: '1K', value: '1K' },
  { label: '2K', value: '2K' },
]
const editResOptions = [
  { label: '512（最短边 512）', value: '512' },
  { label: '1024（最短边 1024）', value: '1024' },
  { label: '1536（最短边 1536）', value: '1536' },
  { label: '2048（最短边 2048）', value: '2048' },
]

interface Model {
  id: string
  name: string
  model: string
  enabled: boolean
}
interface Provider {
  id: string
  name: string
  provider_type: string
  enabled: boolean
  base_url: string
  api_keys: string[]
  timeout_seconds: number
  watermark: boolean
  models: Model[]
  comfyui_workflow_json: string
  comfyui_mapping: Record<string, unknown>
}

const loading = ref(false)
const saving = ref(false)
const providers = ref<Provider[]>([])
const defaultModelId = ref<string | null>(null)
const styleRecommend = ref(false)
const customStyle = ref('')
const templates = ref<Record<string, any>>({})
const baseline = ref('')

// API Keys 输入草稿（按 provider id 暂存，不进持久化数据）
const keyInput = reactive<Record<string, string>>({})
function maskKey(k: string): string {
  if (k.length <= 12) return k
  return `${k.slice(0, 6)}…${k.slice(-4)}`
}
function addKey(p: Provider) {
  const v = (keyInput[p.id] || '').trim()
  if (!v) return
  if (!p.api_keys.includes(v)) p.api_keys.push(v)
  keyInput[p.id] = ''
}

// 前端内置模型→擅长画风预览（与后端 core/config.py 的 MODEL_STYLES 保持一致）
const MODEL_STYLE_PREVIEW: Record<string, string> = {
  seedream: '商业写实/产品广告、杂志风信息图排版、国风传统艺术、潮流动漫手办、影视游戏概念原画',
  'gpt-image': '版式化设计/信息卡片、吉卜力/水彩/绘本、3D Q版/Low Poly/像素/矢量插画',
  gemini: '写实摄影纪实、3D 卡通等距微缩、信息图表商业营销（含清晰字体渲染）',
  sensenova: '扁平插画手绘、专业平面设计商用海报、长卷连环叙事、细腻写实',
}
const currentModelStyle = computed(() => {
  const id = defaultModelId.value
  if (!id) return ''
  const key = id.split('::')[0].toLowerCase()
  const hit = Object.keys(MODEL_STYLE_PREVIEW).find(k => key.includes(k))
  return hit ? MODEL_STYLE_PREVIEW[hit] : ''
})

const modelOptions = computed(() => {
  const opts: { label: string; value: string }[] = []
  for (const p of providers.value) {
    if (!p.enabled) continue
    for (const m of p.models) {
      if (!m.enabled) continue
      const id = `${p.id}::${m.id}`
      opts.push({ label: `${p.name} / ${m.name}`, value: id })
    }
  }
  return opts
})

const dirty = computed(() => {
  if (loading.value) return false
  const cur = JSON.stringify({
    providers: providers.value,
    defaultModelId: defaultModelId.value,
    styleRecommend: styleRecommend.value,
    customStyle: customStyle.value,
  })
  return cur !== baseline.value
})

async function reload() {
  loading.value = true
  try {
    await init()
    const data: any = await apiGet('config')
    const list: Provider[] = (data.providers || []).map((p: any) => ({
      id: p.id,
      name: p.name || '',
      provider_type: p.provider_type || 'openai',
      enabled: p.enabled !== false,
      base_url: p.base_url || '',
      api_keys: Array.isArray(p.api_keys) ? [...p.api_keys] : [],
      timeout_seconds: Number(p.timeout_seconds) || 600,
      watermark: !!p.watermark,
      models: Array.isArray(p.models) ? p.models.map((m: any) => ({
        id: m.id || m.model || '',
        name: m.name || m.model || '',
        model: m.model || m.id || '',
        enabled: m.enabled !== false,
      })) : [],
      comfyui_workflow_json: p.comfyui_workflow_json || '',
      comfyui_mapping: p.comfyui_mapping || {},
    }))
    providers.value = list
    defaultModelId.value = data.default_model_id || null
    styleRecommend.value = !!data.style_recommend
    customStyle.value = data.custom_style || ''
    templates.value = data.templates || {}
    baseline.value = JSON.stringify({
      providers: providers.value,
      defaultModelId: defaultModelId.value,
      styleRecommend: styleRecommend.value,
      customStyle: customStyle.value,
    })
  } catch (e) {
    message.error(`加载失败: ${(e as Error).message}`)
  } finally {
    loading.value = false
  }
}

function addProvider() {
  const ts = Date.now()
  const kind = 'openai'
  const tmpl: any = templates.value[kind] || { name: 'OpenAI Images', base_url: 'https://api.openai.com/v1', model: { name: 'GPT Image 1', model: 'gpt-image-1' } }
  providers.value.push({
    id: `image-provider-${kind}-${ts}`,
    name: tmpl.name || 'OpenAI Images',
    provider_type: kind,
    enabled: true,
    base_url: tmpl.base_url || 'https://api.openai.com/v1',
    api_keys: [],
    timeout_seconds: 600,
    watermark: false,
    models: [{
      id: tmpl?.model?.model || 'gpt-image-1',
      name: tmpl?.model?.name || 'GPT Image 1',
      model: tmpl?.model?.model || 'gpt-image-1',
      enabled: true,
    }],
    comfyui_workflow_json: '',
    comfyui_mapping: {},
  })
}

function onModelNameChange(p: Provider, m: Model, v: string) {
  const oldId = m.id
  const newId = v.trim() || oldId
  const oldFull = `${p.id}::${oldId}`
  const newFull = `${p.id}::${newId}`
  m.model = v
  m.id = newId
  // 草稿同步：若默认指向旧模型，自动跟随新模型名
  if (defaultModelId.value === oldFull) {
    defaultModelId.value = newFull
  }
}

function removeProvider(idx: number) {
  const p = providers.value[idx]
  const prefix = `${p.id}::`
  if (defaultModelId.value && defaultModelId.value.startsWith(prefix)) {
    defaultModelId.value = null
  }
  providers.value.splice(idx, 1)
}

function addModel(p: Provider) {
  p.models.push({
    id: 'gpt-image-1',
    name: '新模型',
    model: 'gpt-image-1',
    enabled: true,
  })
}
function removeModel(p: Provider, idx: number) {
  const full = `${p.id}::${p.models[idx].id}`
  if (defaultModelId.value === full) {
    defaultModelId.value = null
  }
  p.models.splice(idx, 1)
}

async function save() {
  saving.value = true
  try {
    const payload = {
      providers: providers.value.map(p => ({
        ...p,
        timeout_seconds: Number(p.timeout_seconds) || 600,
        api_keys: (p.api_keys || []).filter(Boolean),
        models: p.models.map(m => ({
          id: (m.model || m.id || '').trim() || m.id,
          name: (m.name || '').trim() || (m.model || m.id),
          model: (m.model || m.id || '').trim(),
          enabled: m.enabled !== false,
        })),
      })),
      default_model_id: defaultModelId.value || null,
      style_recommend: !!styleRecommend.value,
      custom_style: customStyle.value.trim(),
    }
    const data: any = await apiPost('config/save', payload)
    // server returns normalized providers/options, keep client in sync
    if (data?.providers) {
      // reload to reflect normalization
      await reload()
    } else {
      baseline.value = JSON.stringify({
        providers: providers.value,
        defaultModelId: defaultModelId.value,
        styleRecommend: styleRecommend.value,
        customStyle: customStyle.value,
      })
    }
    message.success('已保存并即时生效')
  } catch (e) {
    message.error(`保存失败: ${(e as Error).message}`)
  } finally {
    saving.value = false
  }
}

let defaultSaveTimer: number | null = null
async function onDefaultModelChange() {
  if (loading.value) return
  if (!baseline.value) return
  if (defaultSaveTimer) window.clearTimeout(defaultSaveTimer)
  defaultSaveTimer = window.setTimeout(() => {
    void save()
  }, 300) as unknown as number
}

let styleSaveTimer: number | null = null
function onStyleChange() {
  if (loading.value) return
  if (!baseline.value) return
  if (styleSaveTimer) window.clearTimeout(styleSaveTimer)
  styleSaveTimer = window.setTimeout(() => {
    void save()
  }, 300) as unknown as number
}

// ------- 工具测试：两工具全参数 + 本地上传 -------
const toolTab = ref<'generate' | 'edit'>('generate')
const genForm = reactive({
  model_id: null as string | null,
  prompt: 'a cute cat sitting on a cloud, anime style',
  negative_prompt: '',
  size: '1024x1024',
  aspect_ratio: '',
  quality: '',
  n: 1 as number,
  seed: '' as string,
})
const editForm = reactive({
  model_id: null as string | null,
  prompt: '把背景换成海边日落，保留主体',
  negative_prompt: '',
  size: '',
  aspect_ratio: '',
  quality: '',
  seed: '' as string,
})
const genTesting = ref(false)
const genMsg = ref('')
const genPreviews = ref<{ src: string; markdown: string }[]>([])
const editTesting = ref(false)
const editMsg = ref('')
const editPreviews = ref<{ src: string; markdown: string }[]>([])
// 上传：转 data URL 直调后端 _load_image_bytes
const editFileInput = ref<HTMLInputElement | null>(null)
const maskFileInput = ref<HTMLInputElement | null>(null)
const editImages = ref<{ name: string; dataUrl: string }[]>([])
const maskImage = ref<{ name: string; dataUrl: string } | null>(null)

const modelOptionsWithDefault = computed(() => [
  { label: '默认模型（功能设置）', value: '' } as any,
  ...modelOptions.value,
])

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}
function triggerEditPick() { editFileInput.value?.click() }
function triggerMaskPick() { maskFileInput.value?.click() }
async function onEditFiles(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  const remain = 16 - editImages.value.length
  const slice = files.slice(0, Math.max(0, remain))
  if (files.length > remain) message.warning(`最多 16 张，已截取前 ${remain} 张`)
  for (const f of slice) {
    try { editImages.value.push({ name: f.name, dataUrl: await fileToDataUrl(f) }) }
    catch { message.error(`读取失败: ${f.name}`) }
  }
}
function removeEditImage(idx: number) { editImages.value.splice(idx, 1) }
function clearEditImages() { editImages.value = [] }
async function onMaskFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f) return
  try { maskImage.value = { name: f.name, dataUrl: await fileToDataUrl(f) } }
  catch { message.error(`读取失败: ${f.name}`) }
}
function clearMask() { maskImage.value = null }

async function doGenTest(mock: boolean) {
  if (!genForm.prompt.trim()) { message.warning('请输入 prompt'); return }
  genTesting.value = true
  genMsg.value = mock ? 'Mock 生成中...' : '真实生成中...'
  genPreviews.value = []
  try {
    const body: Record<string, unknown> = {
      prompt: genForm.prompt,
      size: genForm.size || undefined,
      aspect_ratio: genForm.aspect_ratio || undefined,
      quality: genForm.quality || undefined,
      negative_prompt: genForm.negative_prompt || undefined,
      n: genForm.n,
      seed: genForm.seed || undefined,
      model_id: genForm.model_id || undefined,
      operation: 'generate',
      mock,
    }
    const data: any = await apiPost('test_generate', body)
    const list: any[] = data.images || (data.b64 ? [data] : [])
    genPreviews.value = list
      .map((it: any) => ({
        src: it.b64 ? `data:${it.mime || 'image/png'};base64,${it.b64}` : '',
        markdown: it.markdown || '',
      }))
      .filter((p: any) => p.src)
    if (!genPreviews.value.length && data.b64) {
      genPreviews.value = [{ src: `data:${data.mime || 'image/png'};base64,${data.b64}`, markdown: '' }]
    }
    genMsg.value = mock ? 'Mock 生成成功' : `生成成功 ${data.provider || ''} ${data.model || ''}`.trim()
    if (!mock) await refreshGenerated()
  } catch (err) {
    genMsg.value = `失败: ${(err as Error).message}`
    message.error(genMsg.value)
  } finally { genTesting.value = false }
}
async function doEditTest(mock: boolean) {
  if (!editForm.prompt.trim()) { message.warning('请输入 prompt'); return }
  if (!editImages.value.length) { message.warning('请先上传输入图片'); return }
  editTesting.value = true
  editMsg.value = mock ? 'Mock 编辑中...' : '真实编辑中...'
  editPreviews.value = []
  try {
    const body: Record<string, unknown> = {
      prompt: editForm.prompt,
      size: editForm.size || undefined,
      aspect_ratio: editForm.aspect_ratio || undefined,
      quality: editForm.quality || undefined,
      negative_prompt: editForm.negative_prompt || undefined,
      seed: editForm.seed || undefined,
      model_id: editForm.model_id || undefined,
      operation: 'edit',
      images: editImages.value.map((it) => it.dataUrl),
      mask: maskImage.value?.dataUrl || undefined,
      mock,
    }
    const data: any = await apiPost('test_generate', body)
    const list: any[] = data.images || (data.b64 ? [data] : [])
    editPreviews.value = list
      .map((it: any) => ({
        src: it.b64 ? `data:${it.mime || 'image/png'};base64,${it.b64}` : '',
        markdown: it.markdown || '',
      }))
      .filter((p: any) => p.src)
    if (!editPreviews.value.length && data.b64) {
      editPreviews.value = [{ src: `data:${data.mime || 'image/png'};base64,${data.b64}`, markdown: '' }]
    }
    editMsg.value = mock ? 'Mock 编辑成功' : `编辑成功 ${data.provider || ''} ${data.model || ''}`.trim()
    if (!mock) await refreshGenerated()
  } catch (err) {
    editMsg.value = `失败: ${(err as Error).message}`
    message.error(editMsg.value)
  } finally { editTesting.value = false }
}

const genLoading = ref(false)
const generated = ref<{ relative_path: string; name: string; date: string }[]>([])
const thumbMap = reactive<Record<string, string>>({})
const previewVisible = ref(false)
const previewSrc = ref('')
const previewTitle = ref('')
const previewPath = ref('')



async function refreshGenerated() {
  genLoading.value = true
  try {
    const list: any = await apiGet('generated')
    generated.value = Array.isArray(list) ? list : []
    // lazy load thumbs for first 12
    for (const it of generated.value.slice(0, 12)) {
      if (thumbMap[it.relative_path]) continue
      void loadThumb(it.relative_path)
    }
  } catch (e) {
    // ignore
  } finally { genLoading.value = false }
}
async function loadThumb(rel: string) {
  try {
    const data: any = await apiGet('image_b64', { path: rel })
    if (data?.b64) thumbMap[rel] = `data:${data.mime || 'image/png'};base64,${data.b64}`
  } catch {}
}
async function openImage(it: { relative_path: string; name: string }) {
  previewTitle.value = it.name
  previewPath.value = it.relative_path
  if (thumbMap[it.relative_path]) {
    previewSrc.value = thumbMap[it.relative_path]
    previewVisible.value = true
  } else {
    try {
      const data: any = await apiGet('image_b64', { path: it.relative_path })
      previewSrc.value = `data:${data.mime || 'image/png'};base64,${data.b64}`
      previewVisible.value = true
    } catch (e) {
      message.error(`加载失败: ${(e as Error).message}`)
    }
  }
}

onMounted(() => { void reload() })
</script>

<style>
.layout {
  display: flex;
  height: 100vh;
}
.sider-inner {
  height: 100%;
  background: var(--glass-thick-bg);
  border-right: 1px solid var(--glass-divider);
  display: flex;
  flex-direction: column;
}
.sider-inner.collapsed .sider-header {
  flex-direction: column;
  justify-content: center;
  padding: 10px 8px;
}
.sider-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--glass-divider);
}
.brand {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
}
.theme-toggle {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: inherit;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  background: var(--glass-regular-bg);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  box-shadow: inset 0 1px 0 var(--glass-highlight), var(--glass-shadow);
  cursor: pointer;
  transition: transform 0.15s ease, background 0.2s ease;
}
.theme-toggle:hover { transform: scale(1.06); }
.theme-toggle:active { transform: scale(0.94); }
.inline-icon { width: 14px; height: 14px; vertical-align: -2px; margin-right: 2px; color: var(--text-3); }
.sider-scroll { flex: 1; }
.sider-footer { padding: 10px 16px; border-top: 1px solid var(--glass-divider); }
.foot-hint { font-size: 12px; color: var(--text-3); word-break: break-all; }
.content { flex: 1; min-width: 0; overflow: hidden; }
.content-scroll { height: 100%; }
.content-inner { max-width: 860px; margin: 0 auto; padding: 20px 26px; }
.content-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
.content-header h2 { font-size: 16px; color: var(--text-1); }
.header-actions { display: flex; gap: 8px; align-items: center; }
.content-sub { font-size: 12px; color: var(--text-3); margin-bottom: 14px; }

.provider-card {
  background: #fff;
  border: 1px solid var(--glass-divider);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin-bottom: 14px;
}
:root[data-theme='dark'] .provider-card { background: rgba(255, 255, 255, 0.04); }
/* 收紧表单：用 n-form-item 的 :show-feedback="false" prop，不覆盖内部类 */
.provider-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.provider-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.provider-name { font-weight: 600; color: var(--text-1); }
.provider-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.hint { font-size: 12px; color: var(--text-3); margin-top: 4px; }
.key-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.models-head { display: flex; align-items: center; justify-content: space-between; margin: 10px 0 6px; }
.models-title { font-size: 12px; color: var(--text-2); font-weight: 600; }
.model-empty { font-size: 12px; color: var(--text-3); padding: 8px; text-align: center; border: 1px dashed var(--glass-divider); border-radius: var(--radius-xs); }
.model-card {
  border: 1px dashed var(--glass-divider);
  background: rgba(0, 0, 0, 0.02);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin-bottom: 8px;
}
:root[data-theme='dark'] .model-card { background: rgba(255,255,255,0.04); }
.model-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.model-name { font-weight: 600; color: var(--text-1); }
.save-bar { display: flex; align-items: center; gap: 12px; margin-top: 6px; flex-wrap: wrap; }

.setting-card {
  margin-top: 6px;
  --n-color: #fff;
  --n-border-color: var(--glass-divider);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
:root[data-theme='dark'] .setting-card { --n-color: rgba(255, 255, 255, 0.04); }
.stat-card { text-align: center; }
.stat-num { font-size: 16px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.tool-info { display: flex; flex-direction: column; gap: 8px; }
.tool-row { display: flex; gap: 10px; align-items: baseline; }
.tool-name { font-family: Consolas, monospace; font-size: 12px; color: var(--accent); background: var(--accent-soft); padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.tool-desc { color: var(--text-2); }
.tool-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 4px; }

.test-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 6px; }
.test-previews { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }
.test-preview { border: 1px solid var(--glass-border); border-radius: var(--radius-md); overflow: hidden; background: var(--glass-regular-bg); }
.test-preview img { width: 100%; display: block; }
.preview-md { font-size: 12px; color: var(--text-3); padding: 8px; word-break: break-all; background: var(--glass-regular-bg); }
.upload-area { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.upload-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; margin-top: 8px; }
.upload-thumb { border: 1px solid var(--glass-border); border-radius: var(--radius-sm); overflow: hidden; background: var(--glass-regular-bg); }
.upload-thumb img { width: 100%; height: 110px; object-fit: cover; display: block; }
.upload-thumb-bar { display: flex; align-items: center; gap: 6px; padding: 4px 6px; }
.upload-thumb-name { flex: 1; min-width: 0; font-size: 12px; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.gen-head { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; margin-bottom: 10px; }
.gen-title { font-weight: 600; color: var(--text-1); }
.img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
.img-card { border: 1px solid var(--glass-border); border-radius: var(--radius-sm); overflow: hidden; background: var(--glass-regular-bg); cursor: pointer; transition: transform 0.15s, border-color 0.15s; }
.img-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.img-card img { width: 100%; height: 140px; object-fit: cover; display: block; }
.img-placeholder { height: 140px; display: flex; align-items: center; justify-content: center; color: var(--text-3); font-size: 16px; background: var(--glass-divider); }
.img-cap { padding: 6px 8px; display: flex; flex-direction: column; gap: 2px; }
.img-name { font-size: 12px; color: var(--text-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.img-date { font-size: 12px; color: var(--text-3); }

.save-fab { position: fixed; right: 26px; bottom: 26px; z-index: 100; box-shadow: var(--glass-shadow); }
.fab-enter-active, .fab-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.fab-enter-from, .fab-leave-to { opacity: 0; transform: translateY(14px) scale(0.92); }
</style>

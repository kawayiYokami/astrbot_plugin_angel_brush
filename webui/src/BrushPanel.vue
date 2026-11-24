<template>
  <!-- 左侧：三个页签导航（240px，可折叠到 56px） -->
  <v-navigation-drawer
    :rail="rail"
    permanent
    width="240"
    rail-width="56"
    class="brush-drawer"
    color="transparent"
  >
    <div class="d-flex flex-column h-100">
      <div class="drawer-head pa-2" :class="rail ? 'd-flex flex-column align-center ga-2' : 'd-flex align-center ga-2'">
        <v-btn
          :icon="rail ? 'lucide:panel-left-open' : 'lucide:panel-left-close'"
          variant="text"
          size="small"
          :aria-label="rail ? '展开侧栏' : '收起侧栏'"
          @click="toggleRail"
        />
        <span v-if="!rail" class="text-subtitle-1 font-weight-medium flex-grow-1 text-truncate">天使的画笔</span>
      </div>

      <v-divider />

      <v-list class="flex-grow-1 overflow-y-auto py-2" nav bg-color="transparent">
        <v-list-item
          v-for="item in navItems"
          :key="item.key"
          :active="activeKey === item.key"
          color="primary"
          @click="onNav(item.key)"
        >
          <template #prepend>
            <v-icon :icon="item.icon" />
          </template>
          <v-list-item-title v-if="!rail">{{ item.label }}</v-list-item-title>
          <v-tooltip v-if="rail" activator="parent" location="end">{{ item.label }}</v-tooltip>
        </v-list-item>
      </v-list>
    </div>
  </v-navigation-drawer>

  <v-main>
    <div class="content-inner">
      <!-- ========== 供应商设置 ========== -->
      <template v-if="activeKey === 'providers'">
        <div class="content-header">
          <div>
            <h2 class="text-h4 mb-0">供应商设置</h2>
            <p class="content-sub text-caption text-medium-emphasis mb-0">
              7 家协议 openai / xai / seedream / gemini / sensenova / modelscope / comfyui，保存后即时生效
            </p>
          </div>
          <div class="d-flex align-center ga-2">
            <v-btn variant="text" prepend-icon="lucide:rotate-ccw" :loading="loading" @click="reload">刷新</v-btn>
            <v-btn color="primary" variant="flat" prepend-icon="lucide:plus" @click="addProvider">供应商</v-btn>
          </div>
        </div>

        <div v-if="loading" class="d-flex justify-center py-12">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <v-empty-state
          v-else-if="!providers.length"
          icon="lucide:server"
          title="还没有供应商"
          text="点上方「供应商」新增第一个"
        />

        <template v-else>
          <v-card
            v-for="(p, pIdx) in providers"
            :key="p.id"
            rounded="md"
            style="margin-bottom: 16px; padding-bottom: 8px;"
            class="provider-card"
          >
            <v-card-text class="config-section" style="padding-bottom: 8px;">
              <div class="d-flex align-center ga-3">
                <v-icon icon="lucide:server" size="small" class="flex-shrink-0" />
                <div class="flex-grow-1 min-w-0">
                  <v-list-item-title class="config-title text-truncate">{{ p.name || '未命名供应商' }}</v-list-item-title>
                  <v-list-item-subtitle class="config-hint">{{ p.provider_type }} · {{ p.models.length }} 个模型</v-list-item-subtitle>
                </div>
                <v-switch v-model="p.enabled" color="primary" hide-details density="compact" inset :aria-label="'启用 ' + (p.name || p.id)" />
                <v-btn
                  variant="text"
                  size="small"
                  icon="lucide:trash-2"
                  color="error"
                  :aria-label="'删除供应商 ' + (p.name || p.id)"
                  @click="confirmRemoveProvider(pIdx)"
                />
              </div>
            </v-card-text>

            <div class="object-config">
              <div class="config-item">
              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">名称</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">如：OpenAI Images</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-text-field v-model="p.name" variant="outlined" density="compact" hide-details class="config-field" />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">类型</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">选择供应商协议类型</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-select v-model="p.provider_type" variant="outlined" density="compact" :items="kindOptions" hide-details class="config-field" />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">Base URL</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">如：https://api.openai.com/v1</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-text-field v-model="p.base_url" variant="outlined" density="compact" hide-details class="config-field" />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">超时（秒）</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">取值 10–600 秒</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-text-field
                    v-model.number="p.timeout_seconds"
                    variant="outlined"
                    density="compact"
                    type="number"
                    :min="10"
                    :max="600"
                    hide-details
                    class="config-field"
                  />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">水印</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">是否在生成图片角落添加水印标识</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-switch v-model="p.watermark" color="primary" hide-details density="compact" inset />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">API Keys</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">支持多 key 轮询，回车添加；留空则不鉴权；聚焦时显示明文便于编辑</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-combobox
                    v-model="p.api_keys"
                    variant="outlined"
                    density="compact"
                    multiple
                    chips
                    closable-chips
                    hide-details
                    class="config-field"
                    @update:focused="(v: boolean) => keysFocus[p.id] = v"
                  >
                    <template #chip="{ item, props: chipProps }">
                      <v-chip v-bind="chipProps" size="small">
                        {{ keysFocus[p.id] ? String(item.title ?? '') : maskKey(String(item.title ?? '')) }}
                      </v-chip>
                    </template>
                  </v-combobox>
                </v-col>
              </v-row>

              <template v-if="p.provider_type === 'comfyui'">
                <v-divider class="config-divider" />
                <v-row class="config-row">
                  <v-col cols="12" class="property-info">
                    <v-list-item density="compact">
                      <v-list-item-title class="property-name">ComfyUI Workflow JSON</v-list-item-title>
                      <v-list-item-subtitle class="property-hint">如：{"prompt": ...}</v-list-item-subtitle>
                    </v-list-item>
                  </v-col>
                  <v-col cols="12" class="config-input">
                    <v-textarea
                      v-model="p.comfyui_workflow_json"
                      variant="outlined"
                      rows="3"
                      hide-details
                      class="config-field"
                    />
                  </v-col>
                </v-row>
              </template>

              <v-divider class="config-divider" />

              <div class="model-block">
              <div class="d-flex align-center ga-2 mt-4 mb-2">
                <span class="text-subtitle-2 font-weight-medium d-flex align-center ga-2">
                  <v-icon icon="lucide:layers" size="small" /> 模型 ({{ p.models.length }})
                </span>
                <v-spacer />
                <v-btn variant="text" size="small" prepend-icon="lucide:plus" @click="addModel(p)">模型</v-btn>
              </div>

              <v-empty-state
                v-if="!p.models.length"
                icon="lucide:layers"
                title="该供应商还没有模型"
                density="compact"
              />

              <v-card
                v-for="(m, mIdx) in p.models"
                :key="m.id"
                variant="tonal"
                rounded="control"
                class="model-card mb-2"
              >
                <div class="d-flex align-center ga-2 px-3 pt-2">
                  <span class="text-body-2 font-weight-medium text-truncate">{{ m.name || m.model }}</span>
                  <v-spacer />
                  <v-switch v-model="m.enabled" color="primary" hide-details density="compact" :aria-label="'启用模型 ' + (m.name || m.model)" />
                  <v-btn
                    variant="text"
                    size="small"
                    icon="lucide:x"
                    :aria-label="'删除模型 ' + (m.name || m.model)"
                    @click="confirmRemoveModel(p, mIdx)"
                  />
                </div>
                <v-card-text class="px-3 pb-3 pt-1">
                  <v-row class="config-row">
                    <v-col cols="12" sm="6" class="property-info">
                      <v-list-item density="compact">
                        <v-list-item-title class="property-name">显示名</v-list-item-title>
                        <v-list-item-subtitle class="property-hint">如：GPT Image 1</v-list-item-subtitle>
                      </v-list-item>
                    </v-col>
                    <v-col cols="12" sm="6" class="config-input">
                      <v-text-field v-model="m.name" variant="outlined" density="compact" hide-details class="config-field" />
                    </v-col>
                  </v-row>
                  <v-row class="config-row">
                    <v-col cols="12" sm="6" class="property-info">
                      <v-list-item density="compact">
                        <v-list-item-title class="property-name">模型名</v-list-item-title>
                        <v-list-item-subtitle class="property-hint">如：gpt-image-1</v-list-item-subtitle>
                      </v-list-item>
                    </v-col>
                    <v-col cols="12" sm="6" class="config-input">
                      <v-text-field
                        :model-value="m.model"
                        variant="outlined"
                        density="compact"
                        hide-details
                        class="config-field"
                        @update:model-value="(v: string) => onModelNameChange(p, m, v)"
                      />
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
              </div>
              </div>
            </div>
          </v-card>
        </template>
      </template>

      <!-- ========== 功能设置 ========== -->
      <template v-else-if="activeKey === 'settings'">
        <div class="content-header mb-4">
          <h2 class="text-h4 mb-0">功能设置</h2>
        </div>

        <div v-if="loading" class="d-flex justify-center py-12">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <v-card v-else rounded="md" style="margin-bottom: 16px; padding-bottom: 8px;" class="setting-card">
          <div class="object-config pt-2">
            <div class="config-item">
              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">生图模型</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">选择默认使用的生图模型，切换后自动保存并即时生效</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-select
                    v-model="defaultModelId"
                    variant="outlined"
                    density="compact"
                    :items="modelOptions"
                    clearable
                    hide-details
                    class="config-field"
                    @update:model-value="onDefaultModelChange"
                  />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" sm="6" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">按模型推荐画风</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">
                      <template v-if="defaultModelId && currentModelStyle">
                        {{ defaultModelId.split('::')[0] }} → {{ currentModelStyle }}
                      </template>
                      <template v-else-if="defaultModelId">
                        当前模型没有内置画风词条，仅勾选也不注入
                      </template>
                      <template v-else>
                        选择生图模型后，这里会显示该模型擅长的画风
                      </template>
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" sm="6" class="config-input">
                  <v-switch
                    v-model="styleRecommend"
                    color="primary"
                    hide-details
                    density="compact"
                    inset
                    @update:model-value="onStyleChange"
                  />
                </v-col>
              </v-row>

              <v-divider class="config-divider" />

              <v-row class="config-row">
                <v-col cols="12" class="property-info">
                  <v-list-item density="compact">
                    <v-list-item-title class="property-name">自定义画风</v-list-item-title>
                    <v-list-item-subtitle class="property-hint">画风偏好（会跟着每次生成一起提交）；留空则不加；可与模型推荐叠加</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="12" class="config-input">
                  <v-textarea
                    v-model="customStyle"
                    variant="outlined"
                    rows="6"
                    auto-grow
                    max-rows="14"
                    hide-details
                    class="config-field"
                    @update:model-value="onStyleChange"
                  />
                </v-col>
              </v-row>
            </div>

            <v-alert
              v-if="!modelOptions.length"
              type="warning"
              variant="tonal"
              class="mx-4 mb-2"
              text="还没有可用模型，请先在供应商设置中添加并启用供应商与模型"
            />
          </div>
        </v-card>
      </template>

      <!-- ========== 工具测试 ========== -->
      <template v-else>
        <div class="content-header mb-1">
          <div>
            <h2 class="text-h4 mb-0">工具测试</h2>
            <p class="content-sub text-caption text-medium-emphasis mb-0">
              不用对话，直接在这里试画图、改图。正式出图会自动存进下方历史
            </p>
          </div>
          <v-btn variant="text" prepend-icon="lucide:rotate-ccw" :loading="genLoading" @click="refreshGenerated">刷新结果</v-btn>
        </div>

        <v-tabs v-model="toolTab" color="primary" class="mb-4">
          <v-tab value="generate">生成图片</v-tab>
          <v-tab value="edit">编辑图片</v-tab>
        </v-tabs>

        <!-- 生图 / 编辑：用 v-tabs 切换 + v-if 面板，避免引入重量级 VWindow/focusTrap -->
        <template v-if="toolTab === 'generate'">
          <v-card rounded="md" variant="flat" color="background" class="tools-card">
              <v-card-text class="pa-5">
                <v-select
                  v-model="genForm.model_id"
                  label="绘画模型"
                  hint="不选则用功能设置里的默认模型"
                  persistent-hint
                  :items="modelOptionsWithDefault"
                  placeholder="用默认模型"
                  clearable
                  hide-details
                />
                <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">画面描述</div>
                <v-textarea
                  v-model="genForm.prompt"
                  label="想要画什么（必填）"
                  placeholder="比如：一只坐在云上的猫，动漫风格"
                  rows="2"
                  auto-grow
                  hide-details
                />
                <v-textarea
                  v-model="genForm.negative_prompt"
                  class="mt-4"
                  label="不想看到的内容"
                  placeholder="比如：模糊、水印、多余的手指"
                  rows="1"
                  auto-grow
                  hide-details
                />
                <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">图片设置</div>
                <v-row dense>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="genForm.size" label="自定义尺寸" placeholder="如 1024x1024" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-select v-model="genForm.size" label="常用尺寸" :items="resOptions" placeholder="选一个预设" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="genForm.aspect_ratio" label="画面比例" placeholder="如 16:9、1:1" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="genForm.quality" label="清晰度" placeholder="比如：标准、高清" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model.number="genForm.n" label="一次画几张" type="number" :min="1" :max="4" hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="genForm.seed" label="复现编号" placeholder="留空每次随机" clearable hide-details />
                  </v-col>
                </v-row>

                <div class="d-flex align-center ga-2 flex-wrap mt-5">
                  <v-btn color="primary" variant="flat" prepend-icon="lucide:flask-conical" :loading="genTesting" @click="doGenTest(true)">模拟生成</v-btn>
                  <v-btn variant="outlined" prepend-icon="lucide:sparkles" :loading="genTesting" @click="doGenTest(false)">正式生成</v-btn>
                  <span v-if="genMsg" class="text-caption" :class="genError ? 'text-error' : 'text-medium-emphasis'">{{ genMsg }}</span>
                </div>

                <div v-if="genTesting" class="d-flex justify-center py-8">
                  <v-progress-circular indeterminate color="primary" />
                </div>
                <template v-else-if="genPreviews.length">
                  <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">生成结果</div>
                  <div class="preview-grid">
                    <v-card v-for="(p, idx) in genPreviews" :key="idx" variant="outlined" rounded="control" class="preview-card">
                      <div class="thumb-box"><img :src="p.src" alt="结果预览" /></div>
                      <div v-if="p.markdown" class="text-caption text-medium-emphasis pa-2 preview-md">{{ p.markdown }}</div>
                    </v-card>
                  </div>
                </template>
              </v-card-text>
            </v-card>
        </template>

        <!-- 编辑 -->
        <template v-else>
          <v-card rounded="md" variant="flat" color="background" class="tools-card">
            <v-card-text class="pa-5">
                <v-select
                  v-model="editForm.model_id"
                  label="绘画模型"
                  hint="不选则用功能设置里的默认模型"
                  persistent-hint
                  :items="modelOptionsWithDefault"
                  placeholder="用默认模型"
                  clearable
                  hide-details
                />
                <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">画面描述</div>
                <v-textarea
                  v-model="editForm.prompt"
                  label="想改成什么样（必填）"
                  placeholder="比如：把背景换成海边日落，保留主体"
                  rows="2"
                  auto-grow
                  hide-details
                />
                <v-textarea
                  v-model="editForm.negative_prompt"
                  class="mt-4"
                  label="不想看到的内容"
                  placeholder="比如：模糊、水印、多余的手指"
                  rows="1"
                  auto-grow
                  hide-details
                />

                <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">要改的图片（必填，可选多张）</div>
                <v-file-input
                  v-model="editFiles"
                  label="选择图片"
                  accept="image/*"
                  multiple
                  prepend-icon="lucide:upload"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                  @update:model-value="onEditFiles"
                />
                <div class="text-caption text-medium-emphasis mt-1">已选 {{ editImages.length }} 张（最多 16 张）</div>
                <div v-if="editImages.length" class="thumb-grid mt-2">
                  <v-card v-for="(it, idx) in editImages" :key="idx" variant="outlined" rounded="control" class="thumb-card">
                    <div class="thumb-box"><img :src="it.dataUrl" :alt="it.name" /></div>
                    <v-card-actions class="px-2 py-1">
                      <span class="text-caption text-truncate flex-grow-1">{{ it.name }}</span>
                      <v-btn variant="text" size="small" icon="lucide:x" color="error" :aria-label="'移除 ' + it.name" @click="removeEditImage(idx)" />
                    </v-card-actions>
                  </v-card>
                </div>

                <v-file-input
                  v-model="maskFiles"
                  class="mt-4"
                  label="只改一部分（可选）"
                  hint="白色的地方会被重画，其他地方不变"
                  persistent-hint
                  accept="image/*"
                  prepend-icon="lucide:upload"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                  @update:model-value="onMaskFile"
                />
                <div v-if="maskImage" class="thumb-grid mt-2">
                  <v-card variant="outlined" rounded="control" class="thumb-card">
                    <div class="thumb-box"><img :src="maskImage.dataUrl" :alt="maskImage.name" /></div>
                    <v-card-actions class="px-2 py-1">
                      <span class="text-caption text-truncate flex-grow-1">{{ maskImage.name }}</span>
                      <v-btn variant="text" size="small" icon="lucide:x" color="error" aria-label="移除局部重画模板" @click="clearMask" />
                    </v-card-actions>
                  </v-card>
                </div>

                <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">图片设置</div>
                <v-row dense>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="editForm.size" label="自定义尺寸" hint="留空按原图大小" persistent-hint placeholder="如 1024" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-select v-model="editForm.size" label="常用尺寸" :items="editResOptions" placeholder="选一个预设" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="editForm.aspect_ratio" label="画面比例" hint="留空按原图" persistent-hint placeholder="如 16:9、1:1" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="editForm.quality" label="清晰度" placeholder="比如：标准、高清" clearable hide-details />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="editForm.seed" label="复现编号" placeholder="留空每次随机" clearable hide-details />
                  </v-col>
                </v-row>

                <v-alert
                  v-if="!editImages.length"
                  type="warning"
                  variant="tonal"
                  class="mt-4"
                  text="先选一张要改的图片，才能开始"
                />

                <div class="d-flex align-center ga-2 flex-wrap mt-5">
                  <v-btn color="primary" variant="flat" prepend-icon="lucide:flask-conical" :loading="editTesting" @click="doEditTest(true)">模拟编辑</v-btn>
                  <v-btn variant="outlined" prepend-icon="lucide:sparkles" :loading="editTesting" @click="doEditTest(false)">正式编辑</v-btn>
                  <span v-if="editMsg" class="text-caption" :class="editError ? 'text-error' : 'text-medium-emphasis'">{{ editMsg }}</span>
                </div>

                <div v-if="editTesting" class="d-flex justify-center py-8">
                  <v-progress-circular indeterminate color="primary" />
                </div>
                <template v-else-if="editPreviews.length">
                  <div class="text-subtitle-1 font-weight-medium mt-6 mb-3">编辑结果</div>
                  <div class="preview-grid">
                    <v-card v-for="(p, idx) in editPreviews" :key="idx" variant="outlined" rounded="control" class="preview-card">
                      <div class="thumb-box"><img :src="p.src" alt="结果预览" /></div>
                      <div v-if="p.markdown" class="text-caption text-medium-emphasis pa-2 preview-md">{{ p.markdown }}</div>
                    </v-card>
                  </div>
                </template>
              </v-card-text>
            </v-card>
        </template>

        <div class="d-flex align-center ga-2 mt-6 mb-3">
          <span class="text-subtitle-1 font-weight-medium d-flex align-center ga-2">
            <v-icon icon="lucide:images" size="small" /> 画过的图（最近 40 张）
          </span>
          <v-chip size="x-small" variant="tonal">{{ generated.length }} 张</v-chip>
        </div>

        <div v-if="genLoading" class="d-flex justify-center py-8">
          <v-progress-circular indeterminate color="primary" />
        </div>
        <v-empty-state
          v-else-if="!generated.length"
          icon="lucide:images"
          title="还没有作品"
          text="在上面画一张，这里会出现成品"
        />
        <div v-else class="img-grid">
          <v-card
            v-for="it in generated"
            :key="it.relative_path"
            variant="outlined"
            rounded="control"
            class="img-card"
            @click="openImage(it)"
          >
            <div v-if="thumbMap[it.relative_path]" class="thumb-box"><img :src="thumbMap[it.relative_path]" :alt="it.name" /></div>
            <div v-else class="img-placeholder d-flex align-center justify-center">
              <v-progress-circular indeterminate size="24" color="primary" />
            </div>
            <v-card-actions class="px-2 py-1 d-flex flex-column align-start">
              <span class="text-caption text-truncate" style="width: 100%">{{ it.name }}</span>
              <span class="text-caption text-medium-emphasis">{{ it.date }}</span>
            </v-card-actions>
          </v-card>
        </div>
      </template>
    </div>

    <!-- 悬浮保存：仅 providers/settings 且脏时显示 -->
    <Transition name="fab">
      <v-btn
        v-if="dirty && activeKey !== 'tools'"
        class="save-fab"
        color="primary"
        variant="flat"
        rounded="pill"
        size="large"
        elevation="6"
        prepend-icon="lucide:save"
        :loading="saving"
        @click="save"
      >
        保存更改
      </v-btn>
    </Transition>

    <!-- 图片预览弹窗 -->
    <v-dialog v-model="previewVisible" max-width="760">
      <v-card rounded="card">
        <v-card-title class="text-subtitle-1 px-4 pt-3 pb-1 text-truncate">{{ previewTitle }}</v-card-title>
        <v-card-text class="px-4 pb-2">
          <div class="preview-stage">
            <img :src="previewSrc" :alt="previewTitle" />
          </div>
          <div v-if="previewPath" class="text-caption text-medium-emphasis mt-2">{{ previewPath }}</div>
        </v-card-text>
        <v-card-actions class="px-4 pb-3">
          <v-spacer />
          <v-btn variant="text" @click="previewVisible = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useBridge } from './composables/useBridge'
import { toast } from './composables/useToast'
import { confirmDialog } from './composables/useConfirm'

const { apiGet, apiPost, init } = useBridge()

// ---------- 侧栏 ----------
type NavKey = 'providers' | 'settings' | 'tools'
const navItems: { key: NavKey; label: string; icon: string }[] = [
  { key: 'providers', label: '供应商设置', icon: 'lucide:server' },
  { key: 'settings', label: '功能设置', icon: 'lucide:settings' },
  { key: 'tools', label: '工具测试', icon: 'lucide:flask-conical' },
]
const activeKey = ref<NavKey>('providers')
const rail = ref(false)
const narrowMql = window.matchMedia('(max-width: 768px)')
const syncRail = () => { rail.value = narrowMql.matches }
onMounted(() => narrowMql.addEventListener('change', syncRail))
onUnmounted(() => narrowMql.removeEventListener('change', syncRail))
syncRail()

function toggleRail() { rail.value = !rail.value }
function onNav(key: NavKey) {
  activeKey.value = key
  if (key === 'tools') void refreshGenerated()
}

// ---------- 选项 ----------
const kindOptions = ['openai', 'xai', 'seedream', 'gemini', 'sensenova', 'modelscope', 'comfyui']
const resOptions = ['512x512', '1024x1024', '1024x1536', '1536x1024', '1K', '2K']
const editResOptions = ['512', '1024', '1536', '2048']

// ---------- 数据模型 ----------
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

/** 每个供应商的 API Keys 输入框是否聚焦：聚焦时 chip 显示明文，失焦后遮蔽 */
const keysFocus = reactive<Record<string, boolean>>({})

/** 遮蔽密钥：sk-abc123efgh → sk-••••••efgh；短串全遮蔽 */
function maskKey(k: string): string {
  const s = String(k || '').trim()
  if (s.length <= 8) return s ? '••••••••' : ''
  return `${s.slice(0, 3)}${'•'.repeat(6)}${s.slice(-4)}`
}

const modelOptions = computed(() => {
  const opts: { title: string; value: string }[] = []
  for (const p of providers.value) {
    if (!p.enabled) continue
    for (const m of p.models) {
      if (!m.enabled) continue
      opts.push({ title: `${p.name} / ${m.name}`, value: `${p.id}::${m.id}` })
    }
  }
  return opts
})

// 前端内置模型→擅长画风预览（与后端 core/config.py 的 MODEL_STYLES 保持一致）
const MODEL_STYLE_PREVIEW: Record<string, string> = {
  seedream: '商业写实/产品广告、杂志风信息图排版、国风传统艺术、潮流动漫手办、影视游戏概念原画',
  'gpt-image': '版式化设计/信息卡片、吉卜力/水彩/绘本、3D Q版/Low Poly/像素/矢量插画',
  gemini: '写实摄影纪实、3D 卡通等距微缩、信息图表商业营销（含清晰字体渲染）',
  sensenova: '扁平插画手绘、专业平面设计商用海报、长卷连环叙事、细腻写实',
  modelscope: '复杂指令遵循与多图编辑、图内中英文文字渲染、写实人像与设计感插画兼顾',
}
const currentModelStyle = computed(() => {
  const id = defaultModelId.value
  if (!id) return ''
  const key = id.split('::')[0].toLowerCase()
  const hit = Object.keys(MODEL_STYLE_PREVIEW).find(k => key.includes(k))
  return hit ? MODEL_STYLE_PREVIEW[hit] : ''
})

const modelOptionsWithDefault = computed(() => [
  { title: '默认模型（功能设置）', value: '' },
  ...modelOptions.value,
])

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
    toast.error(`加载失败: ${(e as Error).message}`)
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
  const newId = String(v || '').trim() || oldId
  const oldFull = `${p.id}::${oldId}`
  const newFull = `${p.id}::${newId}`
  m.model = String(v || '')
  m.id = newId
  if (defaultModelId.value === oldFull) defaultModelId.value = newFull
}

async function confirmRemoveProvider(idx: number) {
  const p = providers.value[idx]
  const ok = await confirmDialog({
    title: '删除供应商',
    text: `删除 ${p.name || p.id}？此操作需保存后生效`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  const prefix = `${p.id}::`
  if (defaultModelId.value && defaultModelId.value.startsWith(prefix)) defaultModelId.value = null
  providers.value.splice(idx, 1)
}

function addModel(p: Provider) {
  p.models.push({ id: 'gpt-image-1', name: '新模型', model: 'gpt-image-1', enabled: true })
}

async function confirmRemoveModel(p: Provider, idx: number) {
  const m = p.models[idx]
  const ok = await confirmDialog({
    title: '删除模型',
    text: `删除模型 ${m.name || m.model}？`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  const full = `${p.id}::${m.id}`
  if (defaultModelId.value === full) defaultModelId.value = null
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
    await apiPost('config/save', payload)
    await reload()
    toast.success('已保存并即时生效')
  } catch (e) {
    toast.error(`保存失败: ${(e as Error).message}`)
  } finally {
    saving.value = false
  }
}

let defaultSaveTimer: number | null = null
function onDefaultModelChange() {
  if (loading.value || !baseline.value) return
  if (defaultSaveTimer) window.clearTimeout(defaultSaveTimer)
  defaultSaveTimer = window.setTimeout(() => { void save() }, 300) as unknown as number
}
let styleSaveTimer: number | null = null
function onStyleChange() {
  if (loading.value || !baseline.value) return
  if (styleSaveTimer) window.clearTimeout(styleSaveTimer)
  styleSaveTimer = window.setTimeout(() => { void save() }, 300) as unknown as number
}

// ---------- 工具测试 ----------
const toolTab = ref<'generate' | 'edit'>('generate')
const genForm = reactive({
  model_id: null as string | null,
  prompt: '',
  negative_prompt: '',
  size: '1024x1024',
  aspect_ratio: '',
  quality: '',
  n: 1 as number,
  seed: '' as string,
})
const editForm = reactive({
  model_id: null as string | null,
  prompt: '',
  negative_prompt: '',
  size: '',
  aspect_ratio: '',
  quality: '',
  seed: '' as string,
})
const genTesting = ref(false)
const genMsg = ref('')
const genError = ref(false)
const genPreviews = ref<{ src: string; markdown: string }[]>([])
const editTesting = ref(false)
const editMsg = ref('')
const editError = ref(false)
const editPreviews = ref<{ src: string; markdown: string }[]>([])

interface PickedImage { name: string; dataUrl: string }
const editFiles = ref<File[]>([])
const maskFiles = ref<File[]>([])
const editImages = ref<PickedImage[]>([])
const maskImage = ref<PickedImage | null>(null)

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}

function asFileArray(files: File | File[] | null): File[] {
  if (!files) return []
  return Array.isArray(files) ? files : [files]
}

async function onEditFiles(files: File | File[] | null) {
  const incoming = asFileArray(files)
  editFiles.value = []
  if (!incoming.length) { editImages.value = []; return }
  const remain = 16 - editImages.value.length
  const slice = incoming.slice(0, Math.max(0, remain))
  if (incoming.length > remain) toast.warning(`最多 16 张，已截取前 ${remain} 张`)
  for (const f of slice) {
    try { editImages.value.push({ name: f.name, dataUrl: await fileToDataUrl(f) }) }
    catch { toast.error(`读取失败: ${f.name}`) }
  }
}
function removeEditImage(idx: number) { editImages.value.splice(idx, 1) }

async function onMaskFile(files: File | File[] | null) {
  const f = asFileArray(files)[0]
  maskFiles.value = []
  if (!f) { maskImage.value = null; return }
  try { maskImage.value = { name: f.name, dataUrl: await fileToDataUrl(f) } }
  catch { toast.error(`读取失败: ${f.name}`) }
}
function clearMask() { maskImage.value = null; maskFiles.value = [] }

function previewsFrom(data: any): { src: string; markdown: string }[] {
  const list: any[] = data?.images || (data?.b64 ? [data] : [])
  const result = list
    .map((it: any) => ({
      src: it.b64 ? `data:${it.mime || 'image/png'};base64,${it.b64}` : '',
      markdown: it.markdown || '',
    }))
    .filter((p: any) => p.src)
  if (!result.length && data?.b64) {
    result.push({ src: `data:${data.mime || 'image/png'};base64,${data.b64}`, markdown: '' })
  }
  return result
}

async function doGenTest(mock: boolean) {
  if (!genForm.prompt.trim()) { toast.warning('先说说想画什么'); return }
  genTesting.value = true
  genError.value = false
  genMsg.value = mock ? '正在试画…' : '正在出图…'
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
    genPreviews.value = previewsFrom(data)
    genMsg.value = mock ? '试画成功' : `出图成功 ${data.provider || ''} ${data.model || ''}`.trim()
    if (!mock) await refreshGenerated()
  } catch (err) {
    genError.value = true
    genMsg.value = `没画出来：${(err as Error).message}`
    toast.error(genMsg.value)
  } finally {
    genTesting.value = false
  }
}

async function doEditTest(mock: boolean) {
  if (!editForm.prompt.trim()) { toast.warning('先说说想改成什么样'); return }
  if (!editImages.value.length) { toast.warning('先选一张要改的图片'); return }
  editTesting.value = true
  editError.value = false
  editMsg.value = mock ? '正在试改…' : '正在改图…'
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
    editPreviews.value = previewsFrom(data)
    editMsg.value = mock ? '试改成功' : `改图成功 ${data.provider || ''} ${data.model || ''}`.trim()
    if (!mock) await refreshGenerated()
  } catch (err) {
    editError.value = true
    editMsg.value = `没改成：${(err as Error).message}`
    toast.error(editMsg.value)
  } finally {
    editTesting.value = false
  }
}

// ---------- 已生成图片 ----------
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
    for (const it of generated.value.slice(0, 12)) {
      if (thumbMap[it.relative_path]) continue
      void loadThumb(it.relative_path)
    }
  } catch {
    // 历史列表拉取失败不打扰用户，保留空态
  } finally {
    genLoading.value = false
  }
}
async function loadThumb(rel: string) {
  try {
    const data: any = await apiGet('image_b64', { path: rel })
    if (data?.b64) thumbMap[rel] = `data:${data.mime || 'image/png'};base64,${data.b64}`
  } catch { /* 单张缩略图失败留占位 */ }
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
      toast.error(`加载失败: ${(e as Error).message}`)
    }
  }
}

onMounted(() => { void reload() })
</script>

<style scoped>
.brush-drawer {
  border-right: 1px solid rgba(var(--v-border-color), 0.12);
  /* drawer 默认吃 surface；侧栏必须跟页面同 background，卡片才配浮出 */
  background-color: rgb(var(--v-theme-background)) !important;
}
/* v-list 默认吃 surface；侧栏里的列表必须透明，否则菜单区比空白亮一档 */
.v-application .brush-drawer .v-list {
  background-color: transparent !important;
}
.drawer-head {
  min-height: 56px;
}

.content-inner {
  max-width: 960px;
  margin: 0 auto;
  padding: 22px 28px 96px;
}
.content-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.content-sub {
  margin-top: 4px;
}

/* ---- 上游 AstrBotConfigV4.vue 行式范式（照抄数值；颜色用 rgb() 包裹主题三元组） ---- */
.v-application .config-section {
  margin-bottom: 4px;
}
.v-application .config-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgb(var(--v-theme-primaryText));
}
.v-application .config-hint {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-secondaryText));
  margin-top: 2px;
}
.v-application .object-config {
  width: 100%;
}
.v-application .config-row {
  margin: 0;
  align-items: center;
  padding: 8px 8px;
  border-radius: 4px;
}
.v-application .config-row:hover {
  background-color: rgba(0, 0, 0, 0.03);
}
.v-application .property-info {
  padding: 0;
}
.v-application .property-name {
  font-size: 0.875rem;
  color: rgb(var(--v-theme-primaryText));
}
.v-application .property-hint {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-secondaryText));
  margin-top: 2px;
}
.v-application .config-input {
  padding: 4px 8px;
}
.v-application .config-field {
  margin-bottom: 0;
}
.v-application .config-divider {
  border-color: rgba(0, 0, 0, 0.1);
  margin-left: 24px;
}
.model-block {
  padding: 0 16px 8px;
}

.provider-card,
.setting-card {
  border-color: rgba(var(--v-border-color), 0.16);
}
/* 工具测试页是真表单：跟页面同色、去边框阴影，靠标题和控件组织信息 */
.tools-card {
  border: none !important;
  box-shadow: none !important;
}
.model-card {
  border-color: rgba(var(--v-border-color), 0.2);
}

.preview-grid,
.thumb-grid,
.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.preview-md {
  word-break: break-all;
}
.thumb-box {
  aspect-ratio: 1;
  width: 100%;
  overflow: hidden;
  border-radius: 4px;
  background: rgba(var(--v-border-color), 0.08);
}
.thumb-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.img-placeholder {
  aspect-ratio: 1;
  background: rgba(var(--v-border-color), 0.08);
}
.img-card {
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}
.img-card:hover {
  transform: translateY(-2px);
  border-color: rgb(var(--v-theme-primary));
}

.preview-stage {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  max-height: 70vh;
  background: rgba(var(--v-border-color), 0.08);
  border-radius: 12px;
  overflow: hidden;
}
.preview-stage img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  display: block;
}

.save-fab {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 100;
}
.fab-enter-active,
.fab-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fab-enter-from,
.fab-leave-to {
  opacity: 0;
  transform: translateY(14px) scale(0.92);
}
</style>

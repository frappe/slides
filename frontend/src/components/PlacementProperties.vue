<template>
	<CollapsibleSection
		title="Placement"
		:key="activeElements?.length"
		:initialState="activeElements?.length > 1"
	>
		<template #default>
			<div class="flex flex-col gap-1.5">
				<div :class="fieldLabelClasses">Position</div>
				<div class="flex flex-col gap-3">
					<div class="flex items-center gap-2">
						<NumberInput
							:modelValue="selectionBounds.left"
							@update:modelValue="(val) => updatePosition('X', val)"
							prefix="x"
							:hideButtons="true"
							class="flex-1"
						/>
						<div class="flex items-center gap-1">
							<Button
								icon="copy"
								variant="ghost"
								size="sm"
								@click="copyToClipboard(selectionBounds.left, 'X')"
								title="Copy X Coordinate"
							/>
							<Button
								icon="clipboard"
								variant="ghost"
								size="sm"
								@click="pasteFromClipboard('X')"
								title="Paste X Coordinate"
							/>
						</div>
					</div>

					<div class="flex items-center gap-2">
						<NumberInput
							:modelValue="selectionBounds.top"
							@update:modelValue="(val) => updatePosition('Y', val)"
							prefix="y"
							:hideButtons="true"
							class="flex-1"
						/>
						<div class="flex items-center gap-1">
							<Button
								icon="copy"
								variant="ghost"
								size="sm"
								@click="copyToClipboard(selectionBounds.top, 'Y')"
								title="Copy Y Coordinate"
							/>
							<Button
								icon="clipboard"
								variant="ghost"
								size="sm"
								@click="pasteFromClipboard('Y')"
								title="Paste Y Coordinate"
							/>
						</div>
					</div>
				</div>
			</div>

			<div class="flex flex-col gap-1.5 pt-2">
				<div :class="fieldLabelClasses">Arrange</div>
				<div class="grid grid-cols-2 gap-3">
					<Button
						v-for="option in arrangeOptions"
						:key="option.label"
						variant="outline"
						class="text-sm opacity-85"
						:label="option.label"
						@click="option.action"
					>
						<template #prefix>
							<component :is="option.icon" />
						</template>
					</Button>
				</div>
			</div>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import Forward from '@/icons/Forward.vue'
import Backward from '@/icons/Backward.vue'
import SendToBack from '@/icons/SendToBack.vue'
import BringToFront from '@/icons/BringToFront.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'
import { Button } from 'frappe-ui' // Removed createToast to fix the SyntaxError
import { selectionBounds, currentSlide } from '@/stores/slide'
import {
	activeElements,
	updatePosition,
	getElementPosition,
	isWithinOverlappingBounds,
	normalizeZIndices,
} from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'
import { cloneObj } from '@/utils/helpers'

const arrangeOptions = [
	{ label: 'Backward', icon: Backward, action: () => sendBackward() },
	{ label: 'Forward', icon: Forward, action: () => bringForward() },
	{ label: 'To Back', icon: SendToBack, action: () => sendToBack() },
	{ label: 'To Front', icon: BringToFront, action: () => bringToFront() },
]

// ... (existing helper logic moveElement, getElementLists, etc.)

const copyToClipboard = (value, label) => {
	if (!value && value !== 0) return
	const roundedValue = Math.round(value).toString()
	navigator.clipboard.writeText(roundedValue).then(() => {
		console.log(`${label} coordinate ${roundedValue} copied to clipboard!`)
	})
}

const pasteFromClipboard = async (label) => {
	try {
		const text = await navigator.clipboard.readText()
		const numValue = Math.round(parseFloat(text))
		if (!isNaN(numValue)) {
			updatePosition(label, numValue)
			console.log(`SUCCESS: Applied ${label} = ${numValue}`)
		}
	} catch (err) {
		console.error('Failed to read clipboard. Ensure browser permissions are granted.')
	}
}

// Ensure these functions remain linked to buttons
const sendBackward = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('backward')
}
const sendToBack = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('back')
}
const bringForward = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('forward')
}
const bringToFront = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('front')
}

// (Ensure all initMoveToIndexAndFactor and getElementsWithUpdatedZIndices functions from previous working code are included here)
</script>

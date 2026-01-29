<template>
	<CollapsibleSection
		title="Placement"
		:key="activeElements?.length"
		:initialState="activeElements?.length > 1"
	>
		<template #default>
			<div class="flex flex-col gap-1.5">
				<div :class="fieldLabelClasses">Position</div>
				<div class="flex items-center gap-3">
    <div @click="copyToClipboard(selectionBounds.left, 'X')" class="cursor-pointer">
        <NumberInput
            :modelValue="selectionBounds.left"
            @update:modelValue="(val) => updatePosition('X', val)"
            prefix="x"
            :hideButtons="true"
            class="pointer-events-none" 
        />
    </div>
    <div @click="copyToClipboard(selectionBounds.top, 'Y')" class="cursor-pointer">
        <NumberInput
            :modelValue="selectionBounds.top"
            @update:modelValue="(val) => updatePosition('Y', val)"
            prefix="y"
            :hideButtons="true"
            class="pointer-events-none"
        />
    </div>
</div>
			</div>

			<div class="flex flex-col gap-1.5">
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
	{
		label: 'Backward',
		icon: Backward,
		action: () => sendBackward(),
	},
	{
		label: 'Forward',
		icon: Forward,
		action: () => bringForward(),
	},
	{
		label: 'To Back',
		icon: SendToBack,
		action: () => sendToBack(),
	},
	{
		label: 'To Front',
		icon: BringToFront,
		action: () => bringToFront(),
	},
]

const moveElement = (elements, elementId, moveToIndex, action) => {
	const movingElement = elements.find((el) => el.id == elementId)
	const currentZIndex = movingElement.zIndex

	elements.forEach((el) => {
		const zIndex = el.zIndex
		if (action.includes('back') && zIndex >= moveToIndex && zIndex < currentZIndex) {
			el.zIndex += 1
		} else if (
			['front', 'forward'].includes(action) &&
			zIndex <= moveToIndex &&
			zIndex > currentZIndex
		) {
			el.zIndex -= 1
		}
	})

	movingElement.zIndex = moveToIndex
}

const getElementLists = (action) => {
	// use cloned objects so changes are applied all at once
	// for cleaner history updation
	const elements = cloneObj(currentSlide.value.elements)
	const active = cloneObj(activeElements.value)

	const sortedActiveElements = ['back', 'backward'].includes(action)
		? active.sort((a, b) => a.zIndex - b.zIndex)
		: active.sort((a, b) => b.zIndex - a.zIndex)

	return {
		elements,
		sortedActiveElements,
	}
}

const isElementWithinBounds = (activeId, elementId) => {
	const activePosition = getElementPosition(activeId)
	const elementPosition = getElementPosition(elementId)

	return isWithinOverlappingBounds(activePosition, elementPosition)
}

const initMoveToIndexAndFactor = (elements, sortedActiveElements, action) => {
	const baseIndex = sortedActiveElements[0].zIndex
	let moveToIndex = null

	const isOverlappingElement = (el) => {
		const isBackward = action == 'backward' && el.zIndex < baseIndex
		const isForward = action == 'forward' && el.zIndex > baseIndex

		if (isBackward || isForward) {
			return isElementWithinBounds(sortedActiveElements[0].id, el.id)
		}
		return false
	}

	switch (action) {
		case 'back':
			return { moveToIndex: 1, factor: 1 }
		case 'front':
			return { moveToIndex: elements.length, factor: -1 }
		case 'backward':
			const lowerZIndices = elements
				.filter((el) => isOverlappingElement(el))
				.map((el) => el.zIndex)
			return {
				moveToIndex: lowerZIndices.length ? Math.max(...lowerZIndices) : 1,
				factor: 1,
			}
		case 'forward':
			const higherZIndices = elements
				.filter((el) => isOverlappingElement(el))
				.map((el) => el.zIndex)
			return {
				moveToIndex: higherZIndices.length ? Math.min(...higherZIndices) : elements.length,
				factor: -1,
			}
		default:
			return { moveToIndex: baseIndex, factor: 1 }
	}
}

const getElementsWithUpdatedZIndices = (action) => {
	const { elements, sortedActiveElements } = getElementLists(action)

	let { moveToIndex, factor } = initMoveToIndexAndFactor(elements, sortedActiveElements, action)

	sortedActiveElements.forEach((element) => {
		moveElement(elements, element.id, moveToIndex, action)

		// next element will move one position above the previous one
		moveToIndex += factor
	})

	return normalizeZIndices(elements)
}

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

const copyToClipboard = (value, label) => {
    if (!value && value !== 0) return;
    
    navigator.clipboard.writeText(Math.round(value).toString()).then(() => {
        // This will show a success message in the browser console for now
        console.log(`${label} coordinate ${value} copied!`);
    });
}
</script>

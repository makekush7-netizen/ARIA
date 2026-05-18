import React, { useEffect, useRef } from 'react'
import { useGLTF } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * AvatarModel Component
 * Renders the 3D Avatar (Male or Female) based on the URL provided.
 */
export default function AvatarModel({
    modelUrl = '/model_female.glb',
    scale = 1,
    position = [0, 0, 0],
    mini = false,
    showWaistUp = false
}) {
    // Load the specific model requested
    const gltf = useGLTF(modelUrl)
    const { scene, animations } = gltf
    const mixerRef = useRef(null)
    const eyeBonesRef = useRef({ left: [], right: [] })
    const idleTimeRef = useRef(0)
    const blinkTimerRef = useRef(0)

    // Adjust position to show from waist up
    const adjustedPosition = showWaistUp
        ? [position[0], position[1], position[2]]
        : position

    // Animation Actions Ref
    const actionsRef = useRef({})

    useEffect(() => {
        // Setup animation mixer
        if (animations && animations.length > 0) {
            const mixer = new THREE.AnimationMixer(scene)
            mixerRef.current = mixer

            // Store actions for easy access
            animations.forEach((clip) => {
                const action = mixer.clipAction(clip)
                actionsRef.current[clip.name.toLowerCase()] = action
                // Don't auto-play everything, just store them
            })

            // Auto-play Idle (Custom 'mainidle' or standard 'idle')
            const idleAction = actionsRef.current['mainidle'] || actionsRef.current['idle'] || Object.values(actionsRef.current)[0]
            if (idleAction) idleAction.play()

            // Loop: Idle <-> Bashful
            if (actionsRef.current['bashful']) {
                setInterval(() => {
                    // Start Bashful
                    const bash = actionsRef.current['bashful']
                    const main = actionsRef.current['mainidle'] || idleAction

                    if (Math.random() > 0.6) { // 40% chance to be bashful
                        bash.reset().fadeIn(0.5).play()
                        main.fadeOut(0.5)
                        setTimeout(() => {
                            main.reset().fadeIn(0.5).play()
                            bash.fadeOut(0.5)
                        }, 4000) // Stay bashful for 4s
                    }
                }, 8000) // Check every 8s
            }
        }
    }, [animations, scene])

    // Bone Finding Logic
    useEffect(() => {
        scene.traverse((node) => {
            // DEBUG: Log all morphs
            if (node.morphTargetDictionary) {
                // console.log(`[AURA] Mesh "${node.name}" has morphs:`, Object.keys(node.morphTargetDictionary))
            }

            if (node.isBone) {
                const n = node.name.toLowerCase()
                // Check all common permutations
                if (n.includes('lefteye') || n === 'eyeleft' || n === 'eye_l' || n.includes('eye.l')) {
                    console.log("[AURA] Found Left Eye Bone:", node.name)
                    eyeBonesRef.current.left.push(node)
                }
                if (n.includes('righteye') || n === 'eyeright' || n === 'eye_r' || n.includes('eye.r')) {
                    console.log("[AURA] Found Right Eye Bone:", node.name)
                    eyeBonesRef.current.right.push(node)
                }
            }
        })
    }, [scene])

    // Handle Active Animation State
    useEffect(() => {
        // Track current idle action instance
        let currentIdle = actionsRef.current['mainidle'] || actionsRef.current['idle'] || Object.values(actionsRef.current)[0]

        const playAction = (name, isOneShot = true) => {
            const action = actionsRef.current[name] || actionsRef.current[Object.keys(actionsRef.current).find(k => k.includes(name))]

            if (action && action !== currentIdle) {
                console.log(`[AURA] Playing Action: ${name}`)

                // Configure Config
                action.reset()
                action.setLoop(isOneShot ? THREE.LoopOnce : THREE.LoopRepeat)
                action.clampWhenFinished = isOneShot
                action.fadeIn(0.5).play()

                // Fade out Idle
                if (currentIdle) currentIdle.fadeOut(0.5)

                // If OneShot, return to idle after
                if (isOneShot) {
                    const duration = action.getClip().duration * 1000
                    setTimeout(() => {
                        action.fadeOut(0.5)
                        if (currentIdle) currentIdle.reset().fadeIn(0.5).play()
                    }, duration - 500) // Fade back just before end
                }
            } else if (!action) {
                console.warn(`[AURA] Animation not found: ${name}`)
            }
        }

        // 1. TALKING (Looping)
        const onTalking = (e) => {
            const isTalking = e.detail
            const talkAction = actionsRef.current['talk'] || actionsRef.current['talking']
            if (isTalking && talkAction) {
                talkAction.reset().fadeIn(0.5).play()
                // Don't fade out idle completely for talk, maybe just blend? 
                // Actually better to fade idle out if talk is full body. 
                // If talk is just hands, we layer. Assuming full body for now:
                // if (currentIdle) currentIdle.fadeOut(0.5) 
            } else if (talkAction) {
                talkAction.fadeOut(0.5)
                // if (currentIdle) currentIdle.reset().fadeIn(0.5).play()
            }
        }

        // 2. EMOTIONS (One Shot triggers)
        const onEmotion = (e) => {
            const emo = e.detail
            // Map emotions to User's specific glb names
            if (emo === 'happy') playAction('waveing', true) || playAction('wave', true)
            if (emo === 'laugh') playAction('laughing', true) || playAction('laugh', true)
            if (emo === 'shock') playAction('surprised', true) || playAction('shock', true)
            if (emo === 'sad') playAction('bashful', false) || playAction('sad', false) // Bashful might be a loop?
            if (emo === 'thankful') playAction('thankful', true)
            if (emo === 'thinking') playAction('thinking', false) // Loop thinking until speech starts
        }

        window.addEventListener('aura:talking', onTalking)
        window.addEventListener('aura:setEmotion', onEmotion)

        return () => {
            window.removeEventListener('aura:talking', onTalking)
            window.removeEventListener('aura:setEmotion', onEmotion)
        }
    }, [animations])


    // Listen for events to control morphs (lip-sync)
    useEffect(() => {
        function onSetMorph(e) {
            const { name, value } = e?.detail || {}
            if (!name || typeof value !== 'number') return
            scene.traverse((node) => {
                if (!node.isMesh) return
                const dict = node.morphTargetDictionary
                const inf = node.morphTargetInfluences
                if (dict && inf) {
                    const idx = dict[name]
                    if (typeof idx === 'number') {
                        inf[idx] = value
                    }
                }
            })
        }
        window.addEventListener('aura:setMorph', onSetMorph)
        return () => window.removeEventListener('aura:setMorph', onSetMorph)
    }, [scene])

    // Listen for eye control
    useEffect(() => {
        function onSetEye(e) {
            let { yaw = 0, pitch = 0 } = e?.detail || {}
            pitch = Math.max(-0.14, Math.min(0.14, pitch))

            const applyToBones = (list, yawVal, pitchVal) => {
                list.forEach((b) => {
                    try {
                        b.rotation.y = yawVal
                        b.rotation.x = pitchVal
                    } catch (err) { }
                })
            }

            applyToBones(eyeBonesRef.current.left, yaw, pitch)
            applyToBones(eyeBonesRef.current.right, yaw, pitch)
        }
        window.addEventListener('aura:setEye', onSetEye)
        return () => window.removeEventListener('aura:setEye', onSetEye)
    }, [scene])

    // Emotion State
    const emotionRef = useRef('neutral')

    // Listen for emotion events
    useEffect(() => {
        const onEmotion = (e) => {
            emotionRef.current = e.detail || 'neutral'
            // Reset after 3 seconds
            setTimeout(() => { emotionRef.current = 'neutral' }, 3000)
        }
        window.addEventListener('aura:setEmotion', onEmotion)
        return () => window.removeEventListener('aura:setEmotion', onEmotion)
    }, [])

    // Animation Loop
    useFrame((state, delta) => {
        if (mixerRef.current) mixerRef.current.update(delta)
        idleTimeRef.current += delta
        blinkTimerRef.current += delta

        // 1. Breathing
        const breathe = 1 + Math.sin(idleTimeRef.current * 1.5) * 0.008
        scene.scale.setScalar(scale * breathe)

        // 2. Blinking (Binocular + Scale Fallback)
        if (blinkTimerRef.current > 4 + Math.random() * 4) {
            blinkTimerRef.current = 0

            // Try Morphs First
            let blinked = false
            scene.traverse((node) => {
                if (node.isMesh && node.morphTargetDictionary) {
                    const dict = node.morphTargetDictionary
                    const leftIdx = dict['eyesClosed'] || dict['eyeBlinkLeft'] || dict['eyeBlink_L'] || dict['Blink'] || dict['blink'] || dict['Eyes_Blink'] || dict['eyes_closed']
                    const rightIdx = dict['eyeBlinkRight'] || dict['eyeBlink_R']

                    if (leftIdx !== undefined) {
                        try { node.morphTargetInfluences[leftIdx] = 1; setTimeout(() => node.morphTargetInfluences[leftIdx] = 0, 150); blinked = true } catch (e) { }
                    }
                    if (rightIdx !== undefined && rightIdx !== leftIdx) {
                        try { node.morphTargetInfluences[rightIdx] = 1; setTimeout(() => node.morphTargetInfluences[rightIdx] = 0, 150); blinked = true } catch (e) { }
                    }
                }
            })

            // Fallback: Scale Eye Meshes if no morph blink
            if (!blinked) {
                const eyeMeshes = []
                scene.traverse(node => {
                    // Find standard eye mesh names
                    if (node.isMesh && (node.name.includes('Eye') || node.name.includes('eye'))) {
                        eyeMeshes.push(node)
                    }
                })

                eyeMeshes.forEach(mesh => {
                    const originalScaleY = mesh.userData.origScaleY || mesh.scale.y
                    mesh.userData.origScaleY = originalScaleY // Cache original
                    mesh.scale.y = 0.1
                    setTimeout(() => { mesh.scale.y = originalScaleY }, 150)
                })
            }
        }

        // 3. Eye Tracking + Saccades
        if (!mini) {
            const camPos = state.camera.position

            // Saccades (Random micro movements)
            const time = state.clock.elapsedTime
            const saccadeX = Math.sin(time * 0.5) * 0.05 + (Math.random() > 0.98 ? (Math.random() - 0.5) * 0.2 : 0)
            const saccadeY = Math.cos(time * 0.3) * 0.05 + (Math.random() > 0.98 ? (Math.random() - 0.5) * 0.1 : 0)

            const trackEye = (bones) => {
                bones.forEach(bone => {
                    const dx = camPos.x
                    const dy = camPos.y - 1.55
                    const dz = camPos.z

                    const targetYaw = Math.atan2(dx, dz) + saccadeX
                    const targetPitch = Math.atan2(dy, Math.sqrt(dx * dx + dz * dz)) + saccadeY // approx pitch

                    const yaw = Math.max(-0.6, Math.min(0.6, targetYaw))
                    const pitch = Math.max(-0.35, Math.min(0.35, -targetPitch))

                    bone.rotation.y = THREE.MathUtils.lerp(bone.rotation.y, yaw, 0.2)
                    bone.rotation.x = THREE.MathUtils.lerp(bone.rotation.x, pitch, 0.2)
                })
            }
            trackEye(eyeBonesRef.current.left)
            trackEye(eyeBonesRef.current.right)
        }
        // 4. EMOTIONAL MORPHS
        scene.traverse((node) => {
            if (node.isMesh && node.morphTargetDictionary && node.morphTargetInfluences) {
                const dict = node.morphTargetDictionary
                const infl = node.morphTargetInfluences

                // Reset all emotions slowly (but NOT blink morphs!)
                const resetMorph = (key) => {
                    // Don't reset blink (eyesClosed) here, handled by blink logic
                    if (key !== 'eyesClosed' && dict[key] !== undefined) {
                        infl[dict[key]] = THREE.MathUtils.lerp(infl[dict[key]], 0, 0.1)
                    }
                }
                ['mouthSmile', 'browInnerUp', 'jawOpen', 'mouthOpen', 'browOuterUp', 'eyeWide', 'mouthFrown', 'browDown'].forEach(resetMorph)

                // Apply Active Emotion
                if (emotionRef.current === 'happy') {
                    if (dict['mouthSmile'] !== undefined) infl[dict['mouthSmile']] = THREE.MathUtils.lerp(infl[dict['mouthSmile']], 1.0, 0.2) // Max smile, faster lerp
                    if (dict['browInnerUp'] !== undefined) infl[dict['browInnerUp']] = THREE.MathUtils.lerp(infl[dict['browInnerUp']], 1.0, 0.2)
                    if (dict['eyeSquintLeft'] !== undefined) infl[dict['eyeSquintLeft']] = THREE.MathUtils.lerp(infl[dict['eyeSquintLeft']], 0.6, 0.2)
                    if (dict['eyeSquintRight'] !== undefined) infl[dict['eyeSquintRight']] = THREE.MathUtils.lerp(infl[dict['eyeSquintRight']], 0.6, 0.2)
                }
                else if (emotionRef.current === 'laugh') {
                    // Laughing: Eyes closed + Mouth jumping
                    if (dict['eyesClosed'] !== undefined) infl[dict['eyesClosed']] = THREE.MathUtils.lerp(infl[dict['eyesClosed']], 1, 0.2)
                    if (dict['mouthSmile'] !== undefined) infl[dict['mouthSmile']] = 1
                    // Oscillate mouthOpen/jawOpen for "Haha" effect
                    const laughVal = 0.2 + Math.abs(Math.sin(state.clock.elapsedTime * 15)) * 0.5
                    const openMorph = dict['mouthOpen'] !== undefined ? 'mouthOpen' : 'jawOpen'
                    if (dict[openMorph] !== undefined) infl[dict[openMorph]] = THREE.MathUtils.lerp(infl[dict[openMorph]], laughVal, 0.2)
                }
                else if (emotionRef.current === 'shock') {
                    // Shock: Mouth open + Brows up + Eyes wide
                    const openMorph = dict['mouthOpen'] !== undefined ? 'mouthOpen' : 'jawOpen'
                    if (dict[openMorph] !== undefined) infl[dict[openMorph]] = THREE.MathUtils.lerp(infl[dict[openMorph]], 0.6, 0.2)

                    // Try browOuterUp, fallback to browInnerUp if not found
                    const browMorph = dict['browOuterUp'] !== undefined ? 'browOuterUp' : 'browInnerUp'
                    if (dict[browMorph] !== undefined) infl[dict[browMorph]] = THREE.MathUtils.lerp(infl[dict[browMorph]], 1, 0.2)

                    if (dict['eyeWide'] !== undefined) infl[dict['eyeWide']] = THREE.MathUtils.lerp(infl[dict['eyeWide']], 1, 0.2)
                }
                else if (emotionRef.current === 'sad') {
                    // Sad: Frown + Brows down
                    // Try multiple "sad" mouth shapes
                    const frown = dict['mouthFrown'] !== undefined ? 'mouthFrown' :
                        dict['mouthRollLower'] !== undefined ? 'mouthRollLower' :
                            dict['mouthShrugLower'] !== undefined ? 'mouthShrugLower' : 'mouthPucker'

                    if (dict[frown] !== undefined) infl[dict[frown]] = THREE.MathUtils.lerp(infl[dict[frown]], 0.8, 0.1)

                    // If no browDown, try lowering browInnerUp to 0 or negative if allowed (usually not)
                    if (dict['browDown'] !== undefined) infl[dict['browDown']] = THREE.MathUtils.lerp(infl[dict['browDown']], 0.8, 0.1)
                }
            }
        })
    })

    return <primitive object={scene} scale={scale} position={adjustedPosition} />
}

// Preload both to avoid lag when switching
useGLTF.preload('/animatedfemalemodel.glb')
useGLTF.preload('/model_male.glb')

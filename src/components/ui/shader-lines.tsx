"use client"

import { useEffect, useRef } from "react"
import * as THREE from "three"

declare global {
  interface Window {
    THREE: any
  }
}

export function ShaderAnimation() {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<{
    camera: any
    scene: any
    renderer: any
    uniforms: any
    animationId: number | null
  }>({
    camera: null,
    scene: null,
    renderer: null,
    uniforms: null,
    animationId: null,
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Clear any existing content
    container.innerHTML = ""

    // Camera
    const camera = new THREE.Camera()
    camera.position.z = 1

    // Scene
    const scene = new THREE.Scene()

    // Geometry
    const geometry = new THREE.PlaneGeometry(2, 2)

    // Uniforms
    const uniforms = {
      time: { value: 1.0 },
      resolution: { value: new THREE.Vector2() },
    }

    // Vertex shader
    const vertexShader = `
      void main() {
        gl_Position = vec4( position, 1.0 );
      }
    `

    // Fragment shader
    const fragmentShader = `
      #define TWO_PI 6.2831853072
      #define PI 3.14159265359

      precision highp float;
      uniform vec2 resolution;
      uniform float time;

      float random (in float x) {
          return fract(sin(x)*1e4);
      }
      float random (vec2 st) {
          return fract(sin(dot(st.xy,
                               vec2(12.9898,78.233)))*
              43758.5453123);
      }

      varying vec2 vUv;

      void main(void) {
        vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);

        vec2 fMosaicScal = vec2(4.0, 2.0);
        vec2 vScreenSize = vec2(256,256);
        uv.x = floor(uv.x * vScreenSize.x / fMosaicScal.x) / (vScreenSize.x / fMosaicScal.x);
        uv.y = floor(uv.y * vScreenSize.y / fMosaicScal.y) / (vScreenSize.y / fMosaicScal.y);

        float t = time*0.06+random(uv.x)*0.4;
        float lineWidth = 0.0008;

        vec3 color = vec3(0.0);
        for(int j = 0; j < 3; j++){
          for(int i=0; i < 5; i++){
            color[j] += lineWidth*float(i*i) / abs(fract(t - 0.01*float(j)+float(i)*0.01)*1.0 - length(uv));
          }
        }

        gl_FragColor = vec4(color[2],color[1],color[0],1.0);
      }
    `

    // Create material
    const material = new THREE.ShaderMaterial({
      uniforms,
      vertexShader,
      fragmentShader,
    })

    // Create mesh and add to scene
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    // Initialize renderer
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.domElement.style.width = '100%'
    renderer.domElement.style.height = '100%'
    renderer.domElement.style.display = 'block'
    container.appendChild(renderer.domElement)

    // Store references
    sceneRef.current = {
      camera,
      scene,
      renderer,
      uniforms,
      animationId: null,
    }

    // Handle resize
    const onWindowResize = () => {
      if (!container || !renderer.domElement) return
      const rect = container.getBoundingClientRect()
      const width = rect.width || window.innerWidth
      const height = rect.height || window.innerHeight
      renderer.setSize(width, height, false)
      uniforms.resolution.value.set(width, height)
    }

    onWindowResize()
    window.addEventListener("resize", onWindowResize)

    // Animation loop
    const animate = () => {
      sceneRef.current.animationId = requestAnimationFrame(animate)
      uniforms.time.value += 0.05
      renderer.render(scene, camera)
    }

    animate()

    return () => {
      window.removeEventListener("resize", onWindowResize)
      if (sceneRef.current.animationId) {
        cancelAnimationFrame(sceneRef.current.animationId)
      }
      renderer.dispose()
      geometry.dispose()
      material.dispose()
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className="w-full h-full absolute inset-0 overflow-hidden pointer-events-none"
    />
  )
}

export default ShaderAnimation

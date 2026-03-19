"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import * as THREE from "three"
import { Line } from "@react-three/drei"

interface NodePoint {
  pos: THREE.Vector3
  color: string
  size: number
}

export function NetworkGraph() {
  const group = useRef<THREE.Group>(null)
  const time = useRef(0)

  const { nodeGeometries, connections } = useMemo(() => {
    // Create nodes representing regulation categories with different colours
    const categories = [
      { color: "#3b82f6", weight: 0.4 },  // blue — primary nodes
      { color: "#22d3ee", weight: 0.35 }, // cyan — secondary
      { color: "#8b5cf6", weight: 0.25 }, // purple — tertiary
    ]

    const nodeCount = 55
    const pts: NodePoint[] = []

    for (let i = 0; i < nodeCount; i++) {
      const cat = categories[Math.floor(Math.random() * 3)]
      const spread = 22
      pts.push({
        pos: new THREE.Vector3(
          (Math.random() - 0.5) * spread,
          (Math.random() - 0.5) * spread * 0.7,
          (Math.random() - 0.5) * 12
        ),
        color: cat.color,
        size: 0.06 + Math.random() * 0.12,
      })
    }

    // Edges — connect nearby nodes
    const connections: { start: THREE.Vector3; end: THREE.Vector3; opacity: number }[] = []
    for (let i = 0; i < nodeCount; i++) {
      for (let j = i + 1; j < nodeCount; j++) {
        const d = pts[i].pos.distanceTo(pts[j].pos)
        if (d < 5.5) {
          connections.push({
            start: pts[i].pos,
            end: pts[j].pos,
            opacity: Math.max(0.04, 0.14 * (1 - d / 5.5)),
          })
        }
      }
    }

    return { nodeGeometries: pts, connections }
  }, [])

  useFrame((state) => {
    if (!group.current) return
    time.current = state.clock.elapsedTime
    group.current.rotation.y += 0.0006
    group.current.rotation.x = Math.sin(time.current * 0.08) * 0.06
    // Gentle parallax on mouse
    group.current.position.x = THREE.MathUtils.lerp(group.current.position.x, state.mouse.x * 1.5, 0.03)
    group.current.position.y = THREE.MathUtils.lerp(group.current.position.y, state.mouse.y * 1.5, 0.03)
  })

  return (
    <group ref={group}>
      {/* Render each node as a point */}
      {nodeGeometries.map((node, i) => (
        <mesh key={i} position={node.pos}>
          <sphereGeometry args={[node.size, 8, 8]} />
          <meshBasicMaterial color={node.color} transparent opacity={0.75} />
        </mesh>
      ))}

      {/* Connection lines */}
      {connections.map((conn, i) => (
        <Line
          key={i}
          points={[conn.start, conn.end]}
          color="#3b82f6"
          opacity={conn.opacity}
          transparent
          lineWidth={0.8}
        />
      ))}
    </group>
  )
}

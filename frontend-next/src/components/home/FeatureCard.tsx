"use client"

import { motion } from "framer-motion"
import { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface FeatureCardProps {
  title: string
  description: string
  icon: LucideIcon
  delay?: number
  accent?: "blue" | "cyan" | "purple" | "emerald"
  badge?: string
}

const accentMap = {
  blue:    { icon: "text-blue-400",    bg: "bg-blue-500/10",   border: "group-hover:border-blue-500/40" },
  cyan:    { icon: "text-cyan-400",    bg: "bg-cyan-500/10",   border: "group-hover:border-cyan-500/40" },
  purple:  { icon: "text-purple-400",  bg: "bg-purple-500/10", border: "group-hover:border-purple-500/40" },
  emerald: { icon: "text-emerald-400", bg: "bg-emerald-500/10",border: "group-hover:border-emerald-500/40" },
}

export function FeatureCard({
  title,
  description,
  icon: Icon,
  delay = 0,
  accent = "blue",
  badge,
}: FeatureCardProps) {
  const a = accentMap[accent]

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.55, delay, ease: "easeOut" }}
      whileHover={{ y: -4, scale: 1.01 }}
      className="group h-full"
    >
      <div
        className={cn(
          "relative h-full glass-card rounded-2xl p-6 transition-all duration-300 overflow-hidden card-glow",
          "border border-slate-800/80",
          a.border
        )}
      >
        {/* Subtle top-gradient accent */}
        <div
          className="absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          style={{ background: `linear-gradient(90deg, transparent, hsla(217,91%,60%,0.5), transparent)` }}
        />

        {/* Icon */}
        <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center mb-5", a.bg)}>
          <Icon className={cn("w-5 h-5", a.icon)} aria-hidden="true" />
        </div>

        {/* Content */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <h3 className="text-base font-semibold text-white leading-snug">{title}</h3>
          {badge && (
            <span className="flex-shrink-0 px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 text-[10px] font-semibold border border-blue-500/20">
              {badge}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>
    </motion.div>
  )
}

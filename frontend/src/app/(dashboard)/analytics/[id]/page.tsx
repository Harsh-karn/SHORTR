"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function AnalyticsPage() {
  const params = useParams()
  const linkId = params.id as string

  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<any[]>([])
  
  // Mock data for initial frontend build before ClickHouse API is wired up
  useEffect(() => {
    // Simulate API fetch delay
    setTimeout(() => {
      setData([
        { name: "Mon", clicks: 12 },
        { name: "Tue", clicks: 45 },
        { name: "Wed", clicks: 32 },
        { name: "Thu", clicks: 80 },
        { name: "Fri", clicks: 55 },
        { name: "Sat", clicks: 10 },
        { name: "Sun", clicks: 5 },
      ])
      setLoading(false)
    }, 500)
  }, [linkId])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Link href="/links">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Analytics</h2>
          <p className="text-muted-foreground">Viewing data for link ID: {linkId}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clicks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">239</div>
            <p className="text-xs text-muted-foreground">+20% from last month</p>
          </CardContent>
        </Card>
      </div>

      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Clicks Over Time</CardTitle>
          <CardDescription>Daily click volume for the past 7 days</CardDescription>
        </CardHeader>
        <CardContent className="pl-2">
          {loading ? (
            <div className="h-[350px] flex items-center justify-center">Loading chart data...</div>
          ) : (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={data}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `${value}`}
                />
                <Tooltip cursor={{ fill: 'rgba(0,0,0,0.05)' }} />
                <Bar dataKey="clicks" fill="currentColor" radius={[4, 4, 0, 0]} className="fill-primary" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

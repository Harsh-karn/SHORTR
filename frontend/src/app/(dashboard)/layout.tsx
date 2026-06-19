import Link from "next/link"
import { BarChart3, Link as LinkIcon, Settings, Home, Key } from "lucide-react"
import { UserButton } from "@clerk/nextjs"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row bg-muted/40">
      {/* Sidebar */}
      <aside className="w-full md:w-64 border-r bg-background">
        <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <BarChart3 className="h-6 w-6" />
            <span>SHORTR</span>
          </Link>
        </div>
        <div className="flex-1 overflow-auto py-2">
          <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
            <Link
              href="/dashboard"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Home className="h-4 w-4" />
              Overview
            </Link>
            <Link
              href="/links"
              className="flex items-center gap-3 rounded-lg bg-muted px-3 py-2 text-primary transition-all hover:text-primary"
            >
              <LinkIcon className="h-4 w-4" />
              Links
            </Link>
            <Link
              href="/api-keys"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Key className="h-4 w-4" />
              API Keys
            </Link>
            <Link
              href="/settings"
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
        {/* Header */}
        <header className="flex h-14 items-center gap-4 border-b bg-background px-6">
            <h1 className="text-lg font-semibold md:text-2xl">Dashboard</h1>
            <div className="ml-auto">
                <UserButton afterSignOutUrl="/" />
            </div>
        </header>

        {children}
      </main>
    </div>
  )
}

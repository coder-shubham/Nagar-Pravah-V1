"use client"

import { SidebarTrigger } from "@/components/ui/sidebar"
import { useSidebar } from "@/components/ui/sidebar"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { usePathname } from "next/navigation"
import Link from "next/link"
import React from "react"

export function Header() {
  const { isMobile } = useSidebar()
  const pathname = usePathname()

  const breadcrumbItems = React.useMemo(() => {
    const pathParts = pathname.split('/').filter(part => part)
    const items = [{ href: '/', name: 'Home' }]
    
    pathParts.forEach((part, index) => {
        const href = '/' + pathParts.slice(0, index + 1).join('/');
        items.push({ href, name: part.charAt(0).toUpperCase() + part.slice(1) });
    });

    return items;
  }, [pathname])

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/80 backdrop-blur-lg px-4 sm:px-6">
      {isMobile && <SidebarTrigger />}
       <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbItems.map((item, index) => (
            <React.Fragment key={item.href}>
              <BreadcrumbItem>
                {index === breadcrumbItems.length - 1 ? (
                   <BreadcrumbPage className="font-headline">{item.name}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link href={item.href}>{item.name}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {index < breadcrumbItems.length - 1 && <BreadcrumbSeparator />}
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
    </header>
  )
}

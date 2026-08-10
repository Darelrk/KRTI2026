import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { QueryProvider } from '../integrations/query-provider'

import appCss from '../styles/app.scss?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        name: 'theme-color',
        content: '#161616',
      },
      {
        title: 'KRTI VTOL Mission Operations',
      },
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="id">
      <head>
        <HeadContent />
      </head>
      <body data-carbon-theme="g100">
        <QueryProvider>{children}</QueryProvider>

        <Scripts />
      </body>
    </html>
  )
}

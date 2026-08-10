import type { ReactNode } from 'react'

type Props = {
  status: ReactNode
  video: ReactNode
  sidebar: ReactNode
  commands: ReactNode
  alert?: ReactNode
}

export function DashboardShell({ status, video, sidebar, commands, alert }: Props) {
  return (
    <main className="mission-dashboard">
      {alert && <div className="mission-dashboard__alert">{alert}</div>}
      {status}
      <section className="mission-dashboard__main">
        {video}
        {sidebar}
      </section>
      {commands}
    </main>
  )
}

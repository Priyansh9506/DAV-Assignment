import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

/** A single headline number with its label and a short context line. */
export function StatTile({
  label,
  value,
  unit,
  context,
  className,
}: {
  label: string
  value: string
  unit?: string
  context?: React.ReactNode
  className?: string
}) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums">
          {value}
          {unit && <span className="ml-1 text-sm font-normal text-muted-foreground">{unit}</span>}
        </CardTitle>
      </CardHeader>
      {context && <CardFooter className="text-sm text-muted-foreground">{context}</CardFooter>}
    </Card>
  )
}

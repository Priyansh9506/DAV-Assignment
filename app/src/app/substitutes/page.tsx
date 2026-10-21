import { redirect } from "next/navigation"

import { FEATURED_GRADE_ID } from "@/lib/steel"

export default function SubstitutesIndex() {
  redirect(`/substitutes/${FEATURED_GRADE_ID}`)
}

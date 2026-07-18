import type { FindingKind, ReviewStatus, Severity } from '../types'

export function formatMoney(amount: string, currency: string, locale = 'en-GB') {
  return new Intl.NumberFormat(locale, { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(amount))
}

export const kindLabel: Record<FindingKind, string> = { finding: 'Verified finding', observation: 'Observation', clean: 'Clean item' }
export const reviewLabel: Record<ReviewStatus, string> = { confirmed: 'Confirmed', rejected: 'Rejected', needs_review: 'Needs review' }
export const severityLabel: Record<Severity, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' }


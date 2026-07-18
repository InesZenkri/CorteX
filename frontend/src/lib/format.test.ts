import { describe, expect, it } from 'vitest'
import { formatMoney, kindLabel, reviewLabel } from './format'

describe('audit presentation helpers', () => {
  it('formats string monetary values without changing the API representation', () => {
    expect(formatMoney('4200000.00', 'EUR', 'de-DE')).toContain('4.200.000')
  })
  it('keeps findings, observations, and clean items explicit', () => {
    expect(kindLabel.finding).toBe('Verified finding')
    expect(kindLabel.observation).toBe('Observation')
    expect(kindLabel.clean).toBe('Clean item')
  })
  it('maps every review state', () => {
    expect(Object.keys(reviewLabel)).toEqual(['confirmed', 'rejected', 'needs_review'])
  })
})

import { describe, expect, it } from 'vitest'
import { errorMessage } from './errors'

const FALLBACK = 'Something went wrong.'

describe('errorMessage', () => {
  it('returns a plain string detail as-is', () => {
    expect(errorMessage('Email or password is incorrect', FALLBACK)).toBe('Email or password is incorrect')
  })

  it('formats a FastAPI validation list with the field name', () => {
    const detail = [{ loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' }]
    expect(errorMessage(detail, FALLBACK)).toBe('Email: value is not a valid email address')
  })

  it('turns snake_case field names into words', () => {
    const detail = [{ loc: ['body', 'period_start'], msg: 'Input should be a valid date' }]
    expect(errorMessage(detail, FALLBACK)).toBe('Period start: Input should be a valid date')
  })

  it('drops the "Value error, " prefix and omits the field for model-level errors', () => {
    const detail = [{ loc: ['body'], msg: 'Value error, Choose a complete calendar month for the reporting period' }]
    expect(errorMessage(detail, FALLBACK)).toBe('Choose a complete calendar month for the reporting period')
  })

  it('joins several issues', () => {
    const detail = [
      { loc: ['body', 'email'], msg: 'bad email' },
      { loc: ['body', 'password'], msg: 'String should have at least 12 characters' },
    ]
    expect(errorMessage(detail, FALLBACK)).toBe('Email: bad email Password: String should have at least 12 characters')
  })

  it.each([undefined, null, '', '   ', [], [{}], { detail: 'x' }])('falls back for %j', (detail) => {
    expect(errorMessage(detail, FALLBACK)).toBe(FALLBACK)
  })
})

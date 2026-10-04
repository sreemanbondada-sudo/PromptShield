import {
  expect,
  test,
} from '@playwright/test'


const API_BASE_URL = 'http://127.0.0.1:8000'

const EXISTING_EVENT = {
  id: 12,
  created_at: '2026-10-04 05:00:00',
  is_malicious: true,
  risk_level: 'high',
  risk_score: 100,
  category: 'prompt_injection',
  recommended_action: 'block',
  contains_sensitive_data: false,
  matched_patterns: [
    'previous-instruction override',
  ],
  sensitive_data_types: [],
  prompt_length: 52,
  previous_hash: 'test-previous-hash',
  event_hash: 'test-current-hash',
}

const SAFE_ANALYSIS = {
  event_id: 13,
  is_malicious: false,
  risk_level: 'low',
  risk_score: 10,
  category: 'safe',
  matched_patterns: [],
  explanation:
    'No known malicious patterns were detected.',
  contains_sensitive_data: false,
  sensitive_findings: [],
  redacted_prompt: 'Explain the solar system.',
  recommended_action: 'allow',
  ml_prediction: false,
  ml_probability: 0.21,
  detection_sources: [],
}


async function respondWithJson(
  route,
  body,
  status = 200,
) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}


async function mockPromptShieldApi(page) {
  await page.route(
    `${API_BASE_URL}/health`,
    async (route) => {
      await respondWithJson(route, {
        status: 'healthy',
      })
    },
  )

  await page.route(
    `${API_BASE_URL}/auth/login`,
    async (route) => {
      const requestBody = (
        route.request().postDataJSON()
      )

      expect(requestBody).toEqual({
        username: 'admin',
        password: 'test-password',
      })

      await respondWithJson(route, {
        access_token: 'playwright-test-token',
        token_type: 'bearer',
        expires_in: 1800,
      })
    },
  )

  await page.route(
    `${API_BASE_URL}/statistics`,
    async (route) => {
      expect(
        route.request().headers().authorization,
      ).toBe('Bearer playwright-test-token')

      await respondWithJson(route, {
        total_scans: 12,
        malicious_prompts: 4,
        sensitive_prompts: 2,
        actions: {
          allow: 5,
          review: 1,
          redact: 2,
          block: 4,
        },
        categories: {
          safe: 5,
          prompt_injection: 4,
          sensitive_data_exposure: 2,
          ml_suspicious_prompt: 1,
        },
      })
    },
  )

  await page.route(
    `${API_BASE_URL}/audit/verify`,
    async (route) => {
      expect(
        route.request().headers().authorization,
      ).toBe('Bearer playwright-test-token')

      await respondWithJson(route, {
        valid: true,
        checked_events: 12,
        legacy_events: 0,
        broken_event_id: null,
      })
    },
  )

  await page.route(
    `${API_BASE_URL}/events?limit=10`,
    async (route) => {
      expect(
        route.request().headers().authorization,
      ).toBe('Bearer playwright-test-token')

      await respondWithJson(route, {
        events: [EXISTING_EVENT],
      })
    },
  )

  await page.route(
    `${API_BASE_URL}/analyze`,
    async (route) => {
      expect(
        route.request().headers().authorization,
      ).toBe('Bearer playwright-test-token')

      expect(
        route.request().postDataJSON(),
      ).toEqual({
        prompt: 'Explain the solar system.',
      })

      await respondWithJson(
        route,
        SAFE_ANALYSIS,
      )
    },
  )
}


test.describe(
  'PromptShield administrator workflow',
  () => {
    test.beforeEach(async ({ page }) => {
      await mockPromptShieldApi(page)
      await page.goto('/')
    })

    test(
      'logs in, analyzes a prompt and investigates an event',
      async ({ page }) => {
        await expect(
          page.getByLabel(/username/i),
        ).toBeVisible()

        await page
          .getByLabel(/username/i)
          .fill('admin')

        await page
          .getByLabel(/password/i)
          .fill('test-password')

        await page.getByRole('button', {
          name: /sign in securely/i,
        }).click()

        await expect(
          page.getByLabel('Prompt to analyze'),
        ).toBeVisible()

        await expect(
          page.getByText('API online'),
        ).toBeVisible()

        await expect(
          page.getByText('Total scans'),
        ).toBeVisible()

        await expect(
          page
            .getByText('Total scans')
            .locator('..'),
        ).toContainText('12')

        await expect(
          page.getByText('Verified'),
        ).toBeVisible()

        await page
          .getByLabel('Prompt to analyze')
          .fill('Explain the solar system.')

        await page.getByRole('button', {
          name: 'Analyze prompt',
        }).click()

        await expect(
          page.locator('strong').filter({
            hasText: /^Allow$/,
          }),
        ).toBeVisible()

        await expect(
          page.getByText('10/100'),
        ).toBeVisible()

        await expect(
          page.getByText('Security event #13'),
        ).toBeVisible()

        await page.getByRole('button', {
          name: 'View details for event #12',
        }).click()

        const investigationDialog = (
          page.getByRole(
            'dialog',
            {
              name: /security event #12/i,
            },
          )
        )

        await expect(
          investigationDialog,
        ).toBeVisible()

        await expect(
          investigationDialog,
        ).toContainText('Prompt Injection')

        await expect(
          investigationDialog,
        ).toContainText(
          'Previous-Instruction Override',
        )

        await expect(
          investigationDialog,
        ).toContainText(
          'test-current-hash',
        )

        await investigationDialog
          .getByRole('button', {
            name: /close/i,
          })
          .click()

        await expect(
          investigationDialog,
        ).not.toBeVisible()
      },
    )

    test(
      'logs out and removes the administrator session',
      async ({ page }) => {
        await page
          .getByLabel(/username/i)
          .fill('admin')

        await page
          .getByLabel(/password/i)
          .fill('test-password')

        await page.getByRole('button', {
          name: /sign in securely/i,
        }).click()

        await expect(
          page.getByLabel('Prompt to analyze'),
        ).toBeVisible()

        const signOutButton = page.getByRole(
          'button',
          {
            name: /sign out/i,
          },
        )

        await expect(
          signOutButton,
        ).toBeVisible()

        await signOutButton.click()

        await expect(
          page.getByRole('heading', {
            name: /administrator sign in/i,
          }),
        ).toBeVisible()

        await expect(
          page.getByLabel(/username/i),
        ).toBeVisible()

        const storedToken = await page.evaluate(
          () => sessionStorage.getItem(
            'promptshield_access_token',
          ),
        )

        expect(storedToken).toBeNull()
      },
    )
  },
)

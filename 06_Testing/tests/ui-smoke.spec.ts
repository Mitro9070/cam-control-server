import { expect, test } from "@playwright/test";

test("UI smoke: connect -> exposure -> image -> logs", async ({ page }) => {
  await page.goto("/ui/");

  await expect(page.getByRole("heading", { name: /панель проверки/i })).toBeVisible();
  await page.getByRole("button", { name: /Проверка сервиса/i }).click();
  await expect(page.locator("#output")).toContainText("INFO");

  await page.getByRole("button", { name: /Подключить/i }).click();
  await page.getByRole("button", { name: /Состояние камеры/i }).click();
  await expect(page.locator("#output")).toContainText("\"connected\": true");

  await page.getByRole("button", { name: /Экспозиция/i }).click();
  await page.getByRole("button", { name: /Старт \(Start\)/i }).click();
  await expect(page.locator("#activeExposureId")).not.toHaveText("none");

  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: /Статус \(Status\)/i }).click();
  await expect(page.locator("#output")).toContainText(/кадр (готов|еще готовится)/i);

  await page.getByRole("button", { name: /Последний кадр/i }).click();
  await expect(page.locator("#output")).toContainText(/Последний кадр|Кадр еще не готов/i);

  await page.getByRole("button", { name: /Логи/i }).click();
  await page.getByRole("button", { name: /Загрузить логи/i }).click();
  await expect(page.locator("#output")).toContainText("Load logs");
});

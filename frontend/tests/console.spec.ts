import {test,expect} from '@playwright/test';
test('demo → tracker → websocket → HUD → selection → pause/resume',async({page})=>{
 await page.goto('/');await expect(page.getByText('CONNECTED',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'START',exact:true}).click();
 await expect(page.locator('.target')).toHaveCount(6,{timeout:45000});
 await expect(page.locator('.feed-tag')).toContainText('DEMO MODE');
 await page.locator('.target').nth(2).click();await expect(page.locator('.target').nth(2)).toHaveClass(/selected/);
 await expect(page.locator('canvas.seeker')).toBeVisible();
 await page.screenshot({path:'../docs/console-demo.png',fullPage:true});
 await page.getByRole('button',{name:'PAUSE',exact:true}).click();
 await expect(page.getByRole('button',{name:'RESUME',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'RESUME',exact:true}).click();
 await page.getByRole('button',{name:'STOP',exact:true}).click();
 await page.getByRole('button',{name:'SETTINGS ↗'}).click();
 await expect(page.getByText('CONSOLE CONFIGURATION')).toBeVisible();
 await page.getByRole('button',{name:'CLOSE ×'}).click();
});

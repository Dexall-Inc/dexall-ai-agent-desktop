// product-identity.ts — the typed build-time product identity.
//
// product-identity.cjs is the single derivation of every name-shaped
// value a variant owns (product name, appId, channel). Dev bundles and
// test runs import the .cjs itself so the derivation exists in exactly
// one place.

import { mkdirSync } from 'node:fs'
// without this rename it breaks due to some bundler injection of the same name
import { createRequire as nodeCreateRequire } from 'node:module'
import path from 'node:path'

import type devIdentity from '../product-identity.cjs'

/** Mirrors product-identity.cjs (see product-identity.d.cts). */
export type ProductIdentity = typeof devIdentity

declare const __HERMES_PRODUCT_IDENTITY__: ProductIdentity

/** The baked identity of this artifact (dev bundles derive it live). */
export const PRODUCT_IDENTITY: Readonly<ProductIdentity> =
  typeof __HERMES_PRODUCT_IDENTITY__ === 'undefined'
    ? Object.freeze(nodeCreateRequire(import.meta.url)('../product-identity.cjs') as ProductIdentity)
    : Object.freeze(__HERMES_PRODUCT_IDENTITY__)

/** Pin before the first userData lookup and single-instance lock. Electron's
 * later display-name changes must not redirect an installed build's state.
 * Stable variants retain their historical userData directory.
 */
export function applyDesktopIdentity(
  app: {
    getPath(name: 'appData' | 'userData'): string
    setPath(name: 'userData', value: string): void
    setName(name: string): void
  },
  identity: Readonly<ProductIdentity> = PRODUCT_IDENTITY
): string | null {
  const stable = !identity.token && identity.appNamePascal === identity.artifactNamePascal
  const currentUserData = stable ? app.getPath('userData') : ''

  const userData = stable
    ? path.basename(currentUserData) === identity.displayName
      ? path.join(path.dirname(currentUserData), identity.windowsExecutableName)
      : currentUserData
    : path.join(app.getPath('appData'), identity.appNamePascal)

  mkdirSync(userData, { recursive: true })
  app.setPath('userData', userData)

  if (stable) {
    return null
  }

  app.setName(identity.displayName)

  return identity.displayName
}

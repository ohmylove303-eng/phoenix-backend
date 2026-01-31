//#region src/db.d.ts
/**
 * Known packages that include native code and require platform-specific builds.
 *
 * These packages cannot be bundled and should be traced as external dependencies most of the time.
 */
declare const NodeNativePackages: readonly string[];
/**
 * Packages that must be externalized (traced as dependencies) rather than bundled,
 * due to bundler compatibility issues with their module format or dynamic imports.
 */
declare const NonBundleablePackages: string[];
//#endregion
export { NodeNativePackages, NonBundleablePackages };
import { t as ExternalsPluginOptions } from "./_chunks/types.mjs";
import { Plugin } from "rollup";

//#region src/plugin.d.ts
declare function externals(opts: ExternalsPluginOptions): Plugin;
//#endregion
export { type ExternalsPluginOptions, externals };
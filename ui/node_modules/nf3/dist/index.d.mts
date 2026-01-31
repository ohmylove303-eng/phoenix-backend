import { NodeNativePackages } from "./db.mjs";
import { n as ExternalsTraceOptions } from "./_chunks/types.mjs";

//#region src/trace.d.ts
declare function traceNodeModules(input: string[], opts: ExternalsTraceOptions): Promise<void>;
//#endregion
export { type ExternalsTraceOptions, NodeNativePackages, traceNodeModules };
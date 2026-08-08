// stylis and stylis-plugin-rtl ship without bundled types; we only pass them to
// emotion's stylisPlugins, so minimal ambient declarations are sufficient.
declare module "stylis" {
  import type { StylisPlugin } from "@emotion/cache";
  export const prefixer: StylisPlugin;
}
declare module "stylis-plugin-rtl" {
  import type { StylisPlugin } from "@emotion/cache";
  const rtlPlugin: StylisPlugin;
  export default rtlPlugin;
}

import { defineConfig, loadEnv } from 'vite';
import { splitVendorChunkPlugin } from 'vite';
import react from '@vitejs/plugin-react';
import { version } from './package.json';

process.env.REACT_APP_VERSION = version;

// Without it dynamic require is not possible in config file
import { createRequire } from "module";
const require = createRequire(import.meta.url);

export default defineConfig(({command, mode}) => {
    let env = loadEnv(mode, process.cwd(), 'REACT_APP_');
    const processEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => key.startsWith('REACT_APP_')));
    env = { ...env, ...processEnv };
    console.log(mode, env);

    let clientPort = undefined;
    if ("GFIBOT_HTTPS_PORT" in process.env) {
        clientPort = parseInt(process.env.GFIBOT_HTTPS_PORT);
    }

    return {
        plugins: [
            react(),
            splitVendorChunkPlugin(),
        ],
        envPrefix: 'REACT_APP_',
        // walkaround for rollup commonjs plugin
        // credit: https://github.com/vitejs/vite/issues/2139#issuecomment-1399098579
        build: {
            outDir: 'build',
            commonjsOptions: {
                defaultIsModuleExports(id) {
                  const module = require(id);
                  if (module?.default) {
                    return false;
                  }
                  return "auto";
                },
              },
        },
        define: {
            __APP_ENV__: env.APP_ENV,
            'process.env': env,
        },
        server: {
            hmr: {
                clientPort: clientPort,
            },
        }
    }
});
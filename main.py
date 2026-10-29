from dify_plugin import DifyPluginEnv, Plugin

# Translation of a long PDF can take several minutes, so allow up to 10 minutes
# per request instead of the SDK default.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=600))

if __name__ == "__main__":
    plugin.run()

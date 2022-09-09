import environs


__all__ = ("env",)

env = environs.Env()
env.read_env(".env")

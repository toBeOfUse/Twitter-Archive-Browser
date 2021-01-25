const path = require("path");

module.exports = function (_env, argv) {
  const isProduction = argv.mode === "production";
  const isDevelopment = !isProduction;
  const HTMLWebpackPlugin = require("html-webpack-plugin");

  return {
    devtool: isDevelopment && "cheap-module-source-map",
    entry: "./frontend/index.js",
    stats: {
      assets: false,
      modules: false,
    },
    output: {
      path: path.resolve(__dirname, "frontend"),
      filename: "assets/js/[name].[contenthash:8].js",
      publicPath: "/",
    },
    plugins: [
      new HTMLWebpackPlugin({
        template: "./frontend/index.html",
        filename: "assets/html/index.html",
      }),
    ],
    module: {
      rules: [
        {
          test: /\.jsx?$/,
          exclude: /node_modules/,
          use: {
            loader: "babel-loader",
            options: {
              cacheDirectory: true,
              cacheCompression: false,
              envName: isProduction ? "production" : "development",
            },
          },
        },
        {
          test: /\.css$/,
          use: ["style-loader", "css-loader"],
        },
      ],
    },
  };
};

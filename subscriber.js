const Document = require("../models/document");
const User = require("../models/user");
const redis = require("redis");

const subscriber = async () => {
  const subscriber = redis.createClient({
    socket: {
      host: process.env.REDIS_HOST,
      port: process.env.REDIS_PORT,
    }
  });
  await subscriber.connect();
  await subscriber.subscribe("result", async (message) => {
    // Parse message
    const result = JSON.parse(message);

    // If result is valid
    if (result.filename && result.data) {
      // Get document
      const document = await Document.findOne({ filename: result.filename });
      if (!document) return;

      // Update user
      await User.updateOne(
        { _id: document.user },
        { idle: true, jobCreatedAt: null }
      );

      // Update document
      document.result.method5 = result.data;
      document.markModified("result");
      document.status = result.data.pages.length > 0 ? "invalid" : "valid";
      await document.save();
    }
  });
};

module.exports = subscriber;

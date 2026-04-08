using ASCOM.ProjectR1;
using System.Collections.Generic;
using Xunit;

namespace ASCOM.ProjectR1.Camera.Tests
{
    public class CameraApiValueReaderTests
    {
        [Fact]
        public void ReadInt_ReadBool_ReadDouble_ReadString_ReturnExpectedValues()
        {
            var data = new Dictionary<string, object>
            {
                { "camera_x_size", 2048 },
                { "connected", true },
                { "cooler_power_percent", 77.5 },
                { "sensor_name", "GreatEyes 9.0" }
            };

            Assert.Equal(2048, CameraApiValueReader.ReadInt(data, "camera_x_size"));
            Assert.True(CameraApiValueReader.ReadBool(data, "connected"));
            Assert.Equal(77.5, CameraApiValueReader.ReadDouble(data, "cooler_power_percent"), 3);
            Assert.Equal("GreatEyes 9.0", CameraApiValueReader.ReadString(data, "sensor_name"));
        }

        [Fact]
        public void ReadRequired_ThrowsKeyNotFound_WhenKeyMissing()
        {
            var data = new Dictionary<string, object>
            {
                { "camera_y_size", 2052 }
            };

            Assert.Throws<KeyNotFoundException>(() => CameraApiValueReader.ReadInt(data, "camera_x_size"));
        }
    }
}

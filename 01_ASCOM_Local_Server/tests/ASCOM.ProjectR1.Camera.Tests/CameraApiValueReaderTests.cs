using System;
using System.Collections.Generic;
using ASCOM.ProjectR1;
using Xunit;

namespace ASCOM.ProjectR1.Camera.Tests;

public class CameraApiValueReaderTests
{
    [Fact]
    public void ReadBool_ReadInt_ReadDouble_ReadString_Work()
    {
        var data = new Dictionary<string, object>
        {
            ["connected"] = true,
            ["width"] = 2048,
            ["temp"] = -18.5,
            ["model"] = "GE 2048 2048 BI NIMO",
        };

        Assert.True(CameraApiValueReader.ReadBool(data, "connected"));
        Assert.Equal(2048, CameraApiValueReader.ReadInt(data, "width"));
        Assert.Equal(-18.5, CameraApiValueReader.ReadDouble(data, "temp"));
        Assert.Equal("GE 2048 2048 BI NIMO", CameraApiValueReader.ReadString(data, "model"));
    }

    [Fact]
    public void ReadRequired_KeyMissing_Throws()
    {
        var data = new Dictionary<string, object>();
        Assert.Throws<KeyNotFoundException>(() => CameraApiValueReader.ReadInt(data, "missing"));
    }

    [Fact]
    public void TryReadString_WhenMissing_ReturnsFalse()
    {
        var ok = CameraApiValueReader.TryReadString(new Dictionary<string, object>(), "pixel_type", out var value);
        Assert.False(ok);
        Assert.Equal(string.Empty, value);
    }

    [Fact]
    public void TryReadInt_WhenPresent_ReturnsTrueAndValue()
    {
        var data = new Dictionary<string, object> { ["height"] = "2052" };
        var ok = CameraApiValueReader.TryReadInt(data, "height", out var value);
        Assert.True(ok);
        Assert.Equal(2052, value);
    }
}

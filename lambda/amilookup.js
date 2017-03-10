var aws = require("aws-sdk") ;
exports.handler = function(event, context, callback) {
    console.log("Event: ", event);
    var responseStatus = "FAILED";
    var responseData = {};
    var ec2 = new aws.EC2({region: "us-east-1"});
    var describeImagesParams = {
        Owners:  ["111111111111"]
    };
    console.log("Params: ", describeImagesParams);

    // AMI by Tags
    ec2.describeImages(describeImagesParams, function(err, describeImagesResult) {
        regex = "(.*)?linux.*"
        if (err) {
            responseData = {Error: "DescribeImages call failed"};
            console.log(responseData.Error + ":\n", err);
        } else {
            console.log("Result: ", describeImagesResult);
            var images = describeImagesResult.Images;
            responseStatus = "Success";
            responseData["Name"] = images[0].Name;
            responseData["DateCreated"] = images[0].CreationDate;
            os = event.os;
            os.toLowerCase();
            if (! os.match(regex)) {
                responseData["Os"] = "yes"
            }
    }
        console.log(responseStatus, responseData);
        callback(null,os);
    });
};



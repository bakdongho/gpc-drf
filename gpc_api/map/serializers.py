from rest_framework import serializers

class StoreSerializer(serializers.Serializer):
    lng = serializers.FloatField(help_text='경도')
    lat = serializers.FloatField(help_text='위도')
    store_name = serializers.CharField(help_text='가게 이름')
    store_url = serializers.URLField(help_text="가게 naver URL")

    def create(self, validated_data):
        raise NotImplementedError

    def update(self, instance, validated_data):
        raise NotImplementedError